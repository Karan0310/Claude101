"""
Job Matcher - Uses Claude to calculate fit percentage and detailed analysis
for each job listing against the candidate's resume profile.
"""
import asyncio
import json
from typing import List

import anthropic

from config.settings import settings
from models.schemas import JobListing, JobMatch, ResumeProfile


MATCH_SYSTEM_PROMPT = """You are an expert recruiter and career coach. Your task is to objectively evaluate how well a candidate's resume matches a specific job listing.
You provide accurate, honest assessments with specific reasoning.
Always respond with valid JSON matching the exact schema provided. Do not include markdown code blocks."""

MATCH_USER_PROMPT = """Evaluate this candidate's fit for the job and return a JSON response.

CANDIDATE PROFILE:
- Name: {name}
- Skills: {skills}
- Experience: {experience_years} years
- Previous Titles: {job_titles}
- Education: {education}
- Certifications: {certifications}
- Summary: {summary}

JOB LISTING:
- Title: {job_title}
- Company: {company}
- Location: {location}
- Description: {description}
- Requirements: {requirements}

Return this exact JSON structure:
{{
  "fit_score": <number 0-100>,
  "match_reasons": ["specific reason 1", "specific reason 2", "specific reason 3"],
  "gap_reasons": ["gap or weakness 1", "gap or weakness 2"],
  "recommendation": "Brief 1-2 sentence recommendation on whether to apply and why",
  "application_tips": ["specific tip to strengthen application 1", "tip 2", "tip 3"]
}}

Scoring guide:
- 85-100: Excellent match, highly qualified
- 70-84: Good match, meets most requirements
- 50-69: Partial match, some gaps but worth applying
- 30-49: Stretch role, significant gaps
- 0-29: Poor match, missing core requirements"""


async def score_job_match(
    profile: ResumeProfile,
    job: JobListing,
    client: anthropic.AsyncAnthropic,
) -> JobMatch:
    """Score a single job listing against the resume profile using Claude."""
    prompt = MATCH_USER_PROMPT.format(
        name=profile.name or "Candidate",
        skills=", ".join(profile.skills[:20]) if profile.skills else "Not specified",
        experience_years=profile.experience_years or "Not specified",
        job_titles=", ".join(profile.job_titles[:5]) if profile.job_titles else "Not specified",
        education=", ".join(profile.education[:3]) if profile.education else "Not specified",
        certifications=", ".join(profile.certifications[:5]) if profile.certifications else "None",
        summary=profile.summary or "Not provided",
        job_title=job.title,
        company=job.company,
        location=job.location or "Not specified",
        description=(job.description or "Not provided")[:2000],
        requirements=(job.requirements or "Not specified")[:1000],
    )

    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=MATCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    result = json.loads(response_text)

    return JobMatch(
        job=job,
        fit_score=float(result.get("fit_score", 50)),
        match_reasons=result.get("match_reasons", []),
        gap_reasons=result.get("gap_reasons", []),
        recommendation=result.get("recommendation", ""),
        application_tips=result.get("application_tips", []),
    )


async def score_all_jobs(
    profile: ResumeProfile,
    jobs: List[JobListing],
    concurrency: int = 3,
) -> List[JobMatch]:
    """
    Score all job listings concurrently with rate limiting.
    Returns matches sorted by fit_score descending.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    semaphore = asyncio.Semaphore(concurrency)

    async def _score_with_semaphore(job: JobListing) -> JobMatch:
        async with semaphore:
            try:
                return await score_job_match(profile, job, client)
            except Exception as e:
                # Return a low-scored match on error rather than crashing
                return JobMatch(
                    job=job,
                    fit_score=0,
                    match_reasons=[],
                    gap_reasons=[f"Error during scoring: {str(e)}"],
                    recommendation="Could not evaluate this listing.",
                    application_tips=[],
                )

    matches = await asyncio.gather(*[_score_with_semaphore(job) for job in jobs])
    return sorted(matches, key=lambda m: m.fit_score, reverse=True)
