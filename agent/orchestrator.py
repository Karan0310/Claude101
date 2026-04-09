"""
Agent Orchestrator - The central coordinator that ties all components together.

Flow:
  1. Parse resume → ResumeProfile
  2. Search jobs → List[JobListing]
  3. Score each job → List[JobMatch] (sorted by fit %)
  4. Persist session to DB
  5. Accept user feedback → trigger evaluation
"""
import uuid
from typing import List, Optional, Callable, Awaitable

from models.schemas import (
    JobMatch,
    ResumeProfile,
    SearchRequest,
    UserFeedback,
)
from agent.resume_parser import parse_resume
from agent.job_searcher import search_all_jobs
from agent.job_matcher import score_all_jobs
from agent.feedback_loop import evaluate_recommendations, format_evaluation_report


# Type alias for progress callbacks (used by CLI / web to stream status updates)
ProgressCallback = Callable[[str], Awaitable[None]]


async def _noop_callback(msg: str) -> None:
    pass


class ResumeJobMatcherAgent:
    """
    Main agent class. Instantiate once per session; call `run()` to execute the
    full pipeline and `submit_feedback()` to collect user ratings.
    """

    def __init__(self):
        self.session_id: str = str(uuid.uuid4())
        self.profile: Optional[ResumeProfile] = None
        self.job_matches: List[JobMatch] = []
        self.feedback: List[UserFeedback] = []
        self._evaluation: Optional[dict] = None

    # ── Main Pipeline ──────────────────────────────────────────────────────────

    async def run(
        self,
        file_content: bytes,
        filename: str,
        search_request: Optional[SearchRequest] = None,
        on_progress: ProgressCallback = _noop_callback,
    ) -> List[JobMatch]:
        """
        Execute the full pipeline:
          parse → search → score → return ranked matches
        """
        if search_request is None:
            search_request = SearchRequest(max_results=10)

        # Step 1: Parse resume
        await on_progress("Parsing resume with Claude AI...")
        self.profile = await parse_resume(file_content, filename)
        await on_progress(f"Resume parsed. Detected {len(self.profile.skills)} skills, "
                          f"{self.profile.experience_years or '?'} years of experience.")

        # Step 2: Search for jobs
        await on_progress("Searching for matching jobs across job boards...")
        jobs = await search_all_jobs(self.profile, search_request)
        await on_progress(f"Found {len(jobs)} job listings. Scoring fit...")

        # Step 3: Score each job
        await on_progress("Analyzing fit percentage for each job (this may take ~30s)...")
        self.job_matches = await score_all_jobs(self.profile, jobs, concurrency=3)
        await on_progress(f"Scoring complete. Top match: {self.job_matches[0].fit_score:.0f}% fit.")

        return self.job_matches

    # ── Feedback ───────────────────────────────────────────────────────────────

    def submit_feedback(self, feedback: UserFeedback) -> None:
        """Record a user's feedback on a job recommendation."""
        # Replace existing feedback for the same job
        self.feedback = [f for f in self.feedback if f.job_id != feedback.job_id]
        self.feedback.append(feedback)
        self._evaluation = None  # Invalidate cached evaluation

    # ── Evaluation ─────────────────────────────────────────────────────────────

    async def evaluate(self) -> dict:
        """Run Claude-powered evaluation of recommendation quality."""
        if not self.profile:
            raise RuntimeError("Agent has not run yet. Call run() first.")

        self._evaluation = await evaluate_recommendations(
            feedback_list=self.feedback,
            job_matches=self.job_matches,
            skills=self.profile.skills,
            experience_years=self.profile.experience_years,
            target_roles=self.profile.preferred_roles,
        )
        return self._evaluation

    async def get_evaluation_report(self) -> str:
        """Get a human-readable evaluation report."""
        evaluation = await self.evaluate()
        return format_evaluation_report(evaluation)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def get_top_matches(self, n: int = 5, min_fit: float = 0) -> List[JobMatch]:
        """Return top N matches above a minimum fit threshold."""
        return [m for m in self.job_matches if m.fit_score >= min_fit][:n]

    def get_match_by_job_id(self, job_id: str) -> Optional[JobMatch]:
        for match in self.job_matches:
            if match.job.id == job_id:
                return match
        return None

    def summary_stats(self) -> dict:
        """Quick summary statistics about the current session."""
        if not self.job_matches:
            return {}
        scores = [m.fit_score for m in self.job_matches]
        return {
            "session_id": self.session_id,
            "total_jobs": len(self.job_matches),
            "avg_fit": round(sum(scores) / len(scores), 1),
            "max_fit": round(max(scores), 1),
            "min_fit": round(min(scores), 1),
            "high_fit_count": sum(1 for s in scores if s >= 70),
            "feedback_count": len(self.feedback),
        }
