"""RAG Career Coach API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.postgres_models import User, ParsedResume, Resume, Job, JobDescription
from app.services.rag_coach import RAGCareerCoach
from app.services.embedding_service import get_embedding_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    resume_id: Optional[str] = None
    job_id: Optional[str] = None


@router.post("/chat")
async def chat_with_coach(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chat with the AI Career Coach, optionally grounded on a specific resume and job."""
    user_context = f"User: {current_user.full_name} ({current_user.email})"

    # Enrich context with selected resume
    if body.resume_id:
        result = await db.execute(
            select(ParsedResume)
            .join(Resume)
            .where(
                Resume.id == uuid.UUID(body.resume_id),
                Resume.user_id == current_user.id,
            )
        )
        parsed = result.scalar_one_or_none()
        if parsed:
            skills = parsed.skills or {}
            all_skills = []
            for sl in skills.values():
                all_skills.extend(sl or [])
            user_context += (
                f"\n\n--- Selected Resume ---"
                f"\nName: {parsed.full_name}"
                f"\nExperience: {parsed.total_years_experience} years"
                f"\nSeniority: {parsed.seniority_level}"
                f"\nSkills: {', '.join(all_skills[:20])}"
            )

    # Enrich context with selected job
    if body.job_id:
        job_result = await db.execute(
            select(Job).where(Job.id == uuid.UUID(body.job_id))
        )
        job = job_result.scalar_one_or_none()
        if job:
            user_context += (
                f"\n\n--- Target Job ---"
                f"\nRole: {job.title} at {job.company}"
                f"\nLocation: {job.location or 'N/A'}"
            )
            # Load job description for required skills
            jd_result = await db.execute(
                select(JobDescription).where(JobDescription.job_id == job.id)
            )
            jd = jd_result.scalar_one_or_none()
            if jd:
                req_skills = ", ".join((jd.required_skills or [])[:10])
                pref_skills = ", ".join((jd.preferred_skills or [])[:5])
                user_context += (
                    f"\nRequired Skills: {req_skills}"
                    f"\nPreferred Skills: {pref_skills}"
                    f"\nMin Experience: {jd.min_years_experience} years"
                )

    # Read optional LLM override headers from frontend Settings
    llm_provider = request.headers.get("x-llm-provider")
    llm_api_key = request.headers.get("x-llm-api-key")
    llm_model = request.headers.get("x-llm-model")

    embedding_service = get_embedding_service()
    coach = RAGCareerCoach(
        embedding_service=embedding_service,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
    )

    history = [{"role": msg.role, "content": msg.content} for msg in body.history]

    response = await coach.chat(
        user_message=body.message,
        conversation_history=history,
        user_context=user_context,
    )

    return {
        "response": response,
        "role": "assistant",
    }
