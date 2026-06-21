"""RAG Career Coach API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.resume import ParsedResume, Resume
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


@router.post("/chat")
async def chat_with_coach(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chat with the AI Career Coach."""
    # Build user context from resume data
    user_context = f"User: {current_user.full_name} ({current_user.email})"

    if body.resume_id:
        import uuid
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
                f"\nResume: {parsed.full_name}, {parsed.total_years_experience} years experience"
                f"\nSkills: {', '.join(all_skills[:15])}"
                f"\nSeniority: {parsed.seniority_level}"
            )

    embedding_service = get_embedding_service()
    coach = RAGCareerCoach(embedding_service=embedding_service)

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
