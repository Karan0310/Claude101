"""
FastAPI Web Application for the Resume-Job Matcher Agent.

Endpoints:
  GET  /                  → Upload page
  POST /analyze           → Upload resume + run agent pipeline
  GET  /results/{sid}     → View results for a session
  POST /feedback          → Submit feedback on a job
  GET  /evaluate/{sid}    → Get evaluation report for a session
  GET  /health            → Health check
"""
import json
import os
import uuid
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from models.schemas import FeedbackRating, SearchRequest, UserFeedback
from agent.orchestrator import ResumeJobMatcherAgent
from storage.database import (
    init_db,
    get_db,
    save_session,
    get_session,
    save_feedback,
    get_session_feedback,
    save_evaluation,
)

app = FastAPI(
    title="Resume-Job Matcher Agent",
    description="AI-powered resume analysis and job matching using Claude",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# In-memory agent store (keyed by session_id) — for multi-user support,
# agents are stored in memory for the duration of a server session.
_agents: dict[str, ResumeJobMatcherAgent] = {}


@app.on_event("startup")
async def startup():
    await init_db()
    os.makedirs(settings.upload_dir, exist_ok=True)


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/results/{session_id}", response_class=HTMLResponse)
async def results_page(request: Request, session_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_session(db, session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")

    profile = json.loads(record.resume_profile_json)
    matches = json.loads(record.job_matches_json)
    feedback_records = await get_session_feedback(db, session_id)

    feedback_by_job = {f.job_id: f.rating for f in feedback_records}

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "session_id": session_id,
            "profile": profile,
            "matches": matches,
            "feedback_by_job": feedback_by_job,
        },
    )


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    location: Optional[str] = Form(default=None),
    remote_ok: bool = Form(default=True),
    max_results: int = Form(default=10),
    additional_keywords: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a resume and run the full job-matching pipeline."""
    # Validate file type
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    ext = os.path.splitext(resume.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed)}",
        )

    # Validate file size
    file_content = await resume.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )

    # Build search request
    keywords = [k.strip() for k in additional_keywords.split(",") if k.strip()] if additional_keywords else []
    search_request = SearchRequest(
        location=location or None,
        remote_ok=remote_ok,
        max_results=max(1, min(30, max_results)),
        additional_keywords=keywords,
    )

    # Run agent
    agent = ResumeJobMatcherAgent()
    try:
        matches = await agent.run(file_content, resume.filename or "resume.pdf", search_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Persist to DB
    profile_dict = agent.profile.model_dump()
    matches_list = [m.model_dump() for m in matches]
    await save_session(db, agent.session_id, profile_dict, matches_list, resume.filename)

    # Store agent in memory for feedback/evaluation
    _agents[agent.session_id] = agent

    return JSONResponse(
        content={
            "session_id": agent.session_id,
            "redirect_url": f"/results/{agent.session_id}",
            "stats": agent.summary_stats(),
        }
    )


@app.post("/feedback")
async def submit_feedback(
    session_id: str = Form(...),
    job_id: str = Form(...),
    job_title: str = Form(...),
    company: str = Form(...),
    rating: str = Form(...),
    applied: bool = Form(default=False),
    notes: Optional[str] = Form(default=None),
    predicted_fit: float = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Submit user feedback on a job recommendation."""
    try:
        rating_enum = FeedbackRating(rating)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid rating: {rating}")

    feedback = UserFeedback(
        job_id=job_id,
        job_title=job_title,
        company=company,
        rating=rating_enum,
        applied=applied,
        notes=notes,
        predicted_fit=predicted_fit,
    )

    # Update in-memory agent
    if session_id in _agents:
        _agents[session_id].submit_feedback(feedback)

    # Persist to DB
    await save_feedback(db, session_id, feedback)

    return JSONResponse(content={"status": "ok", "message": "Feedback saved."})


@app.get("/evaluate/{session_id}")
async def get_evaluation(session_id: str, db: AsyncSession = Depends(get_db)):
    """Run and return the feedback loop evaluation for a session."""
    agent = _agents.get(session_id)
    if not agent:
        # Try to reconstruct from DB
        record = await get_session(db, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse(
            content={
                "error": "Agent session expired. Please re-upload your resume for fresh evaluation.",
                "tip": "Evaluation requires the active agent session to be in memory.",
            }
        )

    evaluation = await agent.evaluate()
    report = await agent.get_evaluation_report()

    # Persist evaluation
    await save_evaluation(
        db,
        session_id=session_id,
        total_jobs=evaluation.get("total_feedback_count", 0),
        relevant_count=int(evaluation.get("precision_score", 0) * evaluation.get("total_feedback_count", 0) / 100),
        avg_fit_score=evaluation.get("avg_predicted_fit", 0),
        precision_score=evaluation.get("precision_score"),
        feedback_summary=report,
    )

    return JSONResponse(content={"evaluation": evaluation, "report": report})


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
