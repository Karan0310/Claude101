from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobSource(str, Enum):
    GOOGLE = "google"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    REMOTIVE = "remotive"
    DEMO = "demo"


class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    REMOTE = "remote"


class ResumeProfile(BaseModel):
    """Structured resume data extracted by Claude"""
    raw_text: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[float] = None
    job_titles: List[str] = Field(default_factory=list)
    companies: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    search_keywords: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)


class JobListing(BaseModel):
    """A job listing from any source"""
    id: Optional[str] = None
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_range: Optional[str] = None
    apply_url: Optional[str] = None
    source: JobSource = JobSource.GOOGLE
    posted_date: Optional[str] = None


class JobMatch(BaseModel):
    """A job with its fit score and analysis"""
    job: JobListing
    fit_score: float = Field(ge=0, le=100, description="Fit percentage 0-100")
    match_reasons: List[str] = Field(default_factory=list)
    gap_reasons: List[str] = Field(default_factory=list)
    recommendation: str = ""
    application_tips: List[str] = Field(default_factory=list)


class FeedbackRating(str, Enum):
    VERY_RELEVANT = "very_relevant"
    RELEVANT = "relevant"
    SOMEWHAT_RELEVANT = "somewhat_relevant"
    NOT_RELEVANT = "not_relevant"


class UserFeedback(BaseModel):
    """User feedback on a job recommendation"""
    job_id: str
    job_title: str
    company: str
    rating: FeedbackRating
    applied: bool = False
    notes: Optional[str] = None
    predicted_fit: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentSession(BaseModel):
    """A full agent session with results"""
    session_id: str
    resume_profile: ResumeProfile
    job_matches: List[JobMatch] = Field(default_factory=list)
    feedback: List[UserFeedback] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"


class SearchRequest(BaseModel):
    """User's job search preferences"""
    location: Optional[str] = None
    job_types: List[JobType] = Field(default_factory=list)
    remote_ok: bool = True
    experience_level: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=30)
    additional_keywords: List[str] = Field(default_factory=list)
