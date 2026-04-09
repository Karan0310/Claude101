"""
Job Searcher - Searches for jobs using SerpAPI (Google Jobs), LinkedIn, and Indeed.
Falls back gracefully if API keys are not configured.
"""
import re
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


# ─── Adzuna (free API key, millions of real jobs globally) ───────────────────

async def search_adzuna_jobs(
    query: str,
    location: Optional[str] = None,
    num_results: int = 10,
    country: str = "us",
) -> List[JobListing]:
    """Search Adzuna jobs — free tier: 1,000 calls/day. Register at developer.adzuna.com"""
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []

    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": min(num_results, 50),
        "what": query,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    jobs = []
    for item in data.get("results", [])[:num_results]:
        salary = None
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        if sal_min and sal_max:
            salary = f"${int(sal_min):,} – ${int(sal_max):,}"
        elif sal_min:
            salary = f"${int(sal_min):,}+"

        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("title", "Unknown Title"),
                company=item.get("company", {}).get("display_name", "Unknown Company"),
                location=item.get("location", {}).get("display_name"),
                description=item.get("description"),
                salary_range=salary,
                apply_url=item.get("redirect_url"),
                source=JobSource.GOOGLE,  # closest enum; Adzuna aggregates all sources
                posted_date=item.get("created", "")[:10] if item.get("created") else None,
            )
        )
    return jobs


# ─── Arbeitnow (free, no API key, EU + remote tech jobs) ─────────────────────

async def search_arbeitnow_jobs(
    query: str,
    num_results: int = 10,
) -> List[JobListing]:
    """Search Arbeitnow — completely free, no auth, tech jobs EU + remote."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"search": query},
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    jobs = []
    for item in data.get("data", [])[:num_results]:
        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("title", "Unknown Title"),
                company=item.get("company_name", "Unknown Company"),
                location=item.get("location") or ("Remote" if item.get("remote") else None),
                description=item.get("description", "")[:1500],
                apply_url=item.get("url"),
                source=JobSource.REMOTIVE,  # reuse as "free board" source
                posted_date=str(item.get("published_at", ""))[:10] or None,
            )
        )
    return jobs


# ─── Himalayas (free, no API key, remote tech jobs) ───────────────────────────

async def search_himalayas_jobs(
    query: str,
    num_results: int = 10,
) -> List[JobListing]:
    """Search Himalayas remote jobs — completely free, no auth."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://himalayas.app/jobs/api",
                params={"q": query, "limit": num_results},
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    jobs = []
    for item in data.get("jobs", [])[:num_results]:
        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("title", "Unknown Title"),
                company=item.get("companyName", "Unknown Company"),
                location=item.get("locationRestrictions") or "Remote",
                description=item.get("description", "")[:1500],
                salary_range=item.get("salary"),
                apply_url=item.get("applicationLink") or item.get("url"),
                source=JobSource.REMOTIVE,
                posted_date=item.get("publishedAt", "")[:10] if item.get("publishedAt") else None,
            )
        )
    return jobs


# ─── Remotive (free, no API key required) ────────────────────────────────────

async def search_remotive_jobs(
    query: str,
    num_results: int = 10,
) -> List[JobListing]:
    """Search real remote jobs via Remotive API — completely free, no auth needed."""
    params = {"search": query, "limit": num_results}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://remotive.com/api/remote-jobs",
                params=params,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    jobs = []
    for item in data.get("jobs", [])[:num_results]:
        # Strip HTML tags from description
        raw_desc = item.get("description", "") or ""
        clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()[:1500]

        jobs.append(
            JobListing(
                id=str(uuid.uuid4()),
                title=item.get("title", "Unknown Title"),
                company=item.get("company_name", "Unknown Company"),
                location=item.get("candidate_required_location") or "Remote",
                description=clean_desc,
                salary_range=item.get("salary") or None,
                apply_url=item.get("url"),
                source=JobSource.REMOTIVE,
                posted_date=item.get("publication_date", "")[:10] if item.get("publication_date") else None,
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
    Priority: SerpAPI/LinkedIn (paid) → Adzuna (free key) → Remotive/Arbeitnow/Himalayas (free) → demo
    """
    queries = _build_search_queries(profile, request)
    location = request.location or profile.location
    all_jobs: List[JobListing] = []
    seen_titles_companies = set()

    def _add_unique(jobs: List[JobListing]):
        for job in jobs:
            key = (job.title.lower().strip(), job.company.lower().strip())
            if key not in seen_titles_companies:
                seen_titles_companies.add(key)
                all_jobs.append(job)

    per_query = max(3, request.max_results // max(len(queries), 1))

    # ── Tier 1: paid API sources ──────────────────────────────────────────────
    for query in queries:
        _add_unique(await search_google_jobs(query, location, per_query))
        _add_unique(await search_linkedin_jobs(query, location, per_query))
        _add_unique(await search_indeed_jobs(query, location, per_query))

    # ── Tier 2: Adzuna (free key, broad global coverage) ─────────────────────
    if settings.adzuna_app_id and settings.adzuna_app_key:
        for query in queries[:2]:
            _add_unique(await search_adzuna_jobs(query, location, per_query))

    # ── Tier 3: free no-key sources (always run to enrich results) ───────────
    primary_query = queries[0] if queries else "software engineer"
    _add_unique(await search_remotive_jobs(primary_query, request.max_results))
    _add_unique(await search_arbeitnow_jobs(primary_query, request.max_results))
    _add_unique(await search_himalayas_jobs(primary_query, request.max_results))

    if not all_jobs:
        all_jobs = _generate_demo_jobs(profile)

    return all_jobs[: request.max_results]


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
                source=JobSource.DEMO,
                posted_date="2 days ago",
            )
        )
    return jobs
