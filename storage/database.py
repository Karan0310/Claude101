import json
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import select

from config.settings import settings
from models.schemas import UserFeedback, FeedbackRating


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_name = Column(String, nullable=True)
    resume_profile_json = Column(Text, nullable=False)
    job_matches_json = Column(Text, nullable=False, default="[]")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeedbackRecord(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    job_id = Column(String, nullable=False)
    job_title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    rating = Column(String, nullable=False)
    applied = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    predicted_fit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    total_jobs = Column(Integer, default=0)
    relevant_count = Column(Integer, default=0)
    avg_fit_score = Column(Float, default=0.0)
    precision_score = Column(Float, nullable=True)
    feedback_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Ensure the URL uses the async aiosqlite driver regardless of what's in .env
_db_url = settings.database_url
if _db_url.startswith("sqlite:///") and "+aiosqlite" not in _db_url:
    _db_url = _db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

engine = create_async_engine(_db_url, echo=settings.debug)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def save_session(
    db: AsyncSession,
    session_id: str,
    resume_profile: dict,
    job_matches: list,
    resume_name: Optional[str] = None,
) -> SessionRecord:
    record = SessionRecord(
        id=session_id,
        resume_name=resume_name,
        resume_profile_json=json.dumps(resume_profile),
        job_matches_json=json.dumps(job_matches),
        status="completed",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_session(db: AsyncSession, session_id: str) -> Optional[SessionRecord]:
    result = await db.execute(select(SessionRecord).where(SessionRecord.id == session_id))
    return result.scalar_one_or_none()


async def save_feedback(
    db: AsyncSession,
    session_id: str,
    feedback: UserFeedback,
) -> FeedbackRecord:
    record = FeedbackRecord(
        session_id=session_id,
        job_id=feedback.job_id,
        job_title=feedback.job_title,
        company=feedback.company,
        rating=feedback.rating.value,
        applied=feedback.applied,
        notes=feedback.notes,
        predicted_fit=feedback.predicted_fit,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_session_feedback(db: AsyncSession, session_id: str) -> List[FeedbackRecord]:
    result = await db.execute(
        select(FeedbackRecord).where(FeedbackRecord.session_id == session_id)
    )
    return result.scalars().all()


async def save_evaluation(
    db: AsyncSession,
    session_id: str,
    total_jobs: int,
    relevant_count: int,
    avg_fit_score: float,
    precision_score: Optional[float],
    feedback_summary: str,
) -> EvaluationRecord:
    record = EvaluationRecord(
        session_id=session_id,
        total_jobs=total_jobs,
        relevant_count=relevant_count,
        avg_fit_score=avg_fit_score,
        precision_score=precision_score,
        feedback_summary=feedback_summary,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
