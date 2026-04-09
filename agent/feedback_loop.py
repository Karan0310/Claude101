"""
Feedback Loop Evaluation System

Collects user feedback on job recommendations and uses Claude to:
1. Evaluate the quality of recommendations
2. Identify patterns in what worked/didn't work
3. Provide improvement insights for future searches
"""
import json
from typing import List, Optional

import anthropic

from config.settings import settings
from models.schemas import FeedbackRating, JobMatch, UserFeedback


EVALUATION_SYSTEM_PROMPT = """You are an AI system evaluator specializing in job recommendation quality assessment.
Analyze user feedback on job recommendations and provide actionable insights.
Always respond with valid JSON. Do not include markdown code blocks."""

EVALUATION_USER_PROMPT = """Analyze the quality of these job recommendations based on user feedback.

JOB MATCHES WITH USER FEEDBACK:
{feedback_details}

CANDIDATE PROFILE SUMMARY:
- Skills: {skills}
- Experience: {experience_years} years
- Target Roles: {target_roles}

Calculate and return this JSON:
{{
  "precision_score": <0-100, % of recommendations rated relevant or very_relevant>,
  "avg_predicted_fit": <average predicted fit score across all jobs>,
  "avg_actual_relevance": <average actual relevance 0-100 based on user ratings>,
  "calibration_assessment": "Was the AI overconfident, underconfident, or well-calibrated?",
  "patterns_found": ["pattern 1 about what worked", "pattern 2 about what didn't"],
  "improvement_suggestions": ["suggestion 1 to improve future searches", "suggestion 2"],
  "overall_quality": "excellent|good|fair|poor",
  "summary": "2-3 sentence summary of recommendation quality and key learnings"
}}

Rating meanings:
- very_relevant: Perfect match, candidate would definitely apply
- relevant: Good match, would consider applying
- somewhat_relevant: Partial match, maybe apply
- not_relevant: Poor match, would not apply"""


def _rating_to_score(rating: FeedbackRating) -> float:
    """Convert rating enum to 0-100 score."""
    return {
        FeedbackRating.VERY_RELEVANT: 95.0,
        FeedbackRating.RELEVANT: 75.0,
        FeedbackRating.SOMEWHAT_RELEVANT: 45.0,
        FeedbackRating.NOT_RELEVANT: 10.0,
    }[rating]


def compute_precision(feedback_list: List[UserFeedback]) -> float:
    """Compute precision: % of recommendations rated relevant or very_relevant."""
    if not feedback_list:
        return 0.0
    relevant = sum(
        1 for f in feedback_list
        if f.rating in (FeedbackRating.VERY_RELEVANT, FeedbackRating.RELEVANT)
    )
    return round(relevant / len(feedback_list) * 100, 1)


def compute_calibration_error(feedback_list: List[UserFeedback]) -> float:
    """Compute mean absolute error between predicted fit and actual relevance scores."""
    if not feedback_list:
        return 0.0
    errors = [
        abs(f.predicted_fit - _rating_to_score(f.rating))
        for f in feedback_list
    ]
    return round(sum(errors) / len(errors), 1)


async def evaluate_recommendations(
    feedback_list: List[UserFeedback],
    job_matches: List[JobMatch],
    skills: List[str],
    experience_years: Optional[float],
    target_roles: List[str],
) -> dict:
    """
    Run Claude-powered evaluation of recommendation quality.
    Returns a structured evaluation report.
    """
    if not feedback_list:
        return {
            "precision_score": 0,
            "avg_predicted_fit": 0,
            "avg_actual_relevance": 0,
            "calibration_assessment": "No feedback provided yet.",
            "patterns_found": [],
            "improvement_suggestions": ["Provide feedback on job recommendations to enable evaluation."],
            "overall_quality": "unknown",
            "summary": "No feedback has been collected yet. Rate the job recommendations to see evaluation insights.",
            "calibration_error": 0,
        }

    # Build feedback details for Claude
    match_by_job_id = {m.job.id: m for m in job_matches}
    feedback_details_parts = []

    for i, fb in enumerate(feedback_list, 1):
        match = match_by_job_id.get(fb.job_id)
        reasons = match.match_reasons[:2] if match else []
        feedback_details_parts.append(
            f"{i}. {fb.job_title} at {fb.company}\n"
            f"   Predicted Fit: {fb.predicted_fit:.0f}%\n"
            f"   User Rating: {fb.rating.value}\n"
            f"   Applied: {'Yes' if fb.applied else 'No'}\n"
            f"   AI Match Reasons: {', '.join(reasons) if reasons else 'N/A'}\n"
            f"   User Notes: {fb.notes or 'None'}"
        )

    feedback_details = "\n\n".join(feedback_details_parts)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=EVALUATION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": EVALUATION_USER_PROMPT.format(
                    feedback_details=feedback_details,
                    skills=", ".join(skills[:10]) if skills else "Not specified",
                    experience_years=experience_years or "Not specified",
                    target_roles=", ".join(target_roles[:5]) if target_roles else "Not specified",
                ),
            }
        ],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    evaluation = json.loads(response_text)

    # Add computed metrics
    evaluation["calibration_error"] = compute_calibration_error(feedback_list)
    evaluation["total_feedback_count"] = len(feedback_list)
    evaluation["applied_count"] = sum(1 for f in feedback_list if f.applied)

    return evaluation


def format_evaluation_report(evaluation: dict) -> str:
    """Format evaluation dict into a human-readable report."""
    quality_emoji = {
        "excellent": "★★★★★",
        "good": "★★★★☆",
        "fair": "★★★☆☆",
        "poor": "★★☆☆☆",
        "unknown": "?????",
    }

    quality = evaluation.get("overall_quality", "unknown")
    emoji = quality_emoji.get(quality, "?????")

    lines = [
        "=" * 60,
        "RECOMMENDATION QUALITY EVALUATION",
        "=" * 60,
        f"Overall Quality: {quality.upper()} {emoji}",
        f"Precision (relevant recommendations): {evaluation.get('precision_score', 0):.1f}%",
        f"Avg Predicted Fit Score: {evaluation.get('avg_predicted_fit', 0):.1f}%",
        f"Avg Actual Relevance Score: {evaluation.get('avg_actual_relevance', 0):.1f}%",
        f"Calibration Error (lower is better): {evaluation.get('calibration_error', 0):.1f} points",
        f"Jobs Rated: {evaluation.get('total_feedback_count', 0)}",
        f"Applications Submitted: {evaluation.get('applied_count', 0)}",
        "",
        "CALIBRATION ASSESSMENT:",
        evaluation.get("calibration_assessment", "N/A"),
        "",
        "PATTERNS FOUND:",
    ]
    for p in evaluation.get("patterns_found", []):
        lines.append(f"  • {p}")

    lines += ["", "IMPROVEMENT SUGGESTIONS:"]
    for s in evaluation.get("improvement_suggestions", []):
        lines.append(f"  → {s}")

    lines += [
        "",
        "SUMMARY:",
        evaluation.get("summary", ""),
        "=" * 60,
    ]

    return "\n".join(lines)
