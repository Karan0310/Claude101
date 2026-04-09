"""
Job Searcher - Searches for jobs using SerpAPI (Google Jobs), LinkedIn, and Indeed.
Falls back gracefully if API keys are not configured.
"""
import uuid
import json
from typing import List, Optional
import httpx

from config.settings import settings
from models.schemas import JobListing, JobSource, SearchRequest, ResumeProfile


# ─── SerpAPI / Google Jobs ────────────────────────────────────────────────────

async def search_google_jobs(
    query: str,
    location: Optional[str] = None,
    num_results: int = 10,
) -> List[JobListing]:
    """Search Google Jobs via SerpAPI."""
    if not settings.serpapi_key:
        return []

    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": settings.serpapi_key,
        "num": num_results,
        "hl": "en",
    }
    if location:
        params["location"] = location

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data.get("jobs_results", [])[:num_results]:
        salary = None
        detected = item.get("detected_extensions", {})
        if detected.get("salary"):
            salary = detected["salary"]

        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("title", "Unknown Title"),
                company=item.get("company_name", "Unknown Company"),
                location=item.get("location"),
                description=item.get("description"),
                salary_range=salary,
                apply_url=item.get("apply_options", [{}])[0].get("link") if item.get("apply_options") else None,
                source=JobSource.GOOGLE,
                posted_date=detected.get("posted_at"),
            )
        )
    return jobs


# ─── LinkedIn Jobs via RapidAPI ───────────────────────────────────────────────

async def search_linkedin_jobs(
    query: str,
    location: Optional[str] = None,
    num_results: int = 10,
) -> List[JobListing]:
    """Search LinkedIn Jobs via RapidAPI."""
    if not settings.rapidapi_key:
        return []

    headers = {
        "x-rapidapi-host": "linkedin-jobs-search.p.rapidapi.com",
        "x-rapidapi-key": settings.rapidapi_key,
        "Content-Type": "application/json",
    }
    payload = {
        "search_terms": query,
        "location": location or "United States",
        "page": "1",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://linkedin-jobs-search.p.rapidapi.com/",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data[:num_results]:
        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("job_title", "Unknown Title"),
                company=item.get("company_name", "Unknown Company"),
                location=item.get("job_location"),
                description=item.get("job_description"),
                apply_url=item.get("linkedin_job_url_cleaned") or item.get("linkedin_job_url"),
                source=JobSource.LINKEDIN,
                posted_date=item.get("posted_date"),
            )
        )
    return jobs


# ─── Indeed Jobs via SerpAPI ──────────────────────────────────────────────────

async def search_indeed_jobs(
    query: str,
    location: Optional[str] = None,
    num_results: int = 10,
) -> List[JobListing]:
    """Search Indeed jobs via SerpAPI."""
    if not settings.serpapi_key:
        return []

    params = {
        "engine": "indeed",
        "q": query,
        "api_key": settings.serpapi_key,
        "num": num_results,
    }
    if location:
        params["l"] = location

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data.get("jobs_results", [])[:num_results]:
        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("title", "Unknown Title"),
                company=item.get("company_name", "Unknown Company"),
                location=item.get("location"),
                description=item.get("snippet"),
                salary_range=item.get("salary"),
                apply_url=item.get("link"),
                source=JobSource.INDEED,
                posted_date=item.get("date"),
            )
        )
    return jobs


# ─── Orchestrated multi-source search ────────────────────────────────────────

def _build_search_queries(profile: ResumeProfile, request: SearchRequest) -> List[str]:
    """Build targeted search queries from resume profile."""
    queries = []

    # Primary query from preferred roles
    if profile.preferred_roles:
        primary_role = profile.preferred_roles[0]
        if request.remote_ok:
            queries.append(f"{primary_role} remote")
        queries.append(primary_role)

    # Keyword-based queries
    if profile.search_keywords:
        top_keywords = profile.search_keywords[:5]
        queries.append(" ".join(top_keywords[:3]))

    # Skill-focused queries
    if profile.skills:
        top_skills = profile.skills[:3]
        if profile.preferred_roles:
            queries.append(f"{profile.preferred_roles[0]} {' '.join(top_skills[:2])}")

    # Additional user-specified keywords
    if request.additional_keywords:
        queries.append(" ".join(request.additional_keywords))

    return list(dict.fromkeys(queries))[:4]  # deduplicate, max 4 queries


async def search_all_jobs(
    profile: ResumeProfile,
    request: SearchRequest,
) -> List[JobListing]:
    """
    Search across all configured job sources and return deduplicated results.
    """
    queries = _build_search_queries(profile, request)
    location = request.location or profile.location
    all_jobs: List[JobListing] = []
    seen_titles_companies = set()

    per_query = max(3, request.max_results // len(queries)) if queries else request.max_results

    for query in queries:
        # Google Jobs (primary)
        google_jobs = await search_google_jobs(query, location, per_query)
        all_jobs.extend(google_jobs)

        # LinkedIn
        linkedin_jobs = await search_linkedin_jobs(query, location, per_query)
        all_jobs.extend(linkedin_jobs)

        # Indeed (via SerpAPI)
        indeed_jobs = await search_indeed_jobs(query, location, per_query)
        all_jobs.extend(indeed_jobs)

    # Deduplicate by (title, company)
    unique_jobs = []
    for job in all_jobs:
        key = (job.title.lower().strip(), job.company.lower().strip())
        if key not in seen_titles_companies:
            seen_titles_companies.add(key)
            unique_jobs.append(job)

    if not unique_jobs:
        # Return mock jobs as demo when no API keys are configured
        unique_jobs = _generate_demo_jobs(profile)

    return unique_jobs[: request.max_results]


def _generate_demo_jobs(profile: ResumeProfile) -> List[JobListing]:
    """
    Generate plausible demo job listings when no API keys are available.
    These are clearly labeled as demo data.
    """
    role = profile.preferred_roles[0] if profile.preferred_roles else "Software Engineer"
    skills_str = ", ".join(profile.skills[:3]) if profile.skills else "relevant skills"
    location = profile.location or "Remote"

    demo_companies = [
        ("TechCorp Inc.", "https://example.com/apply/1"),
        ("InnovateCo", "https://example.com/apply/2"),
        ("DataDriven LLC", "https://example.com/apply/3"),
        ("CloudScale Systems", "https://example.com/apply/4"),
        ("NextGen Solutions", "https://example.com/apply/5"),
    ]

    jobs = []
    for i, (company, url) in enumerate(demo_companies):
        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=f"{role}" if i == 0 else f"Lead {role}" if i == 1 else f"Senior {role}" if i == 2 else f"Staff {role}" if i == 3 else f"Principal {role}",
                company=company,
                location=location if i % 2 == 0 else "Remote",
                description=(
                    f"[DEMO - Configure API keys for real jobs] "
                    f"We are looking for a talented {role} with experience in {skills_str}. "
                    f"Join our growing team and make an impact."
                ),
                requirements=f"3+ years of experience. Skills: {skills_str}",
                salary_range="$80,000 - $140,000",
                apply_url=url,
                source=JobSource.GOOGLE,
                posted_date="2 days ago",
            )
        )
    return jobs
