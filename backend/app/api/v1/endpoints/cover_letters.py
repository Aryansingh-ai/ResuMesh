"""
Cover letter generation and listing endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.postgres_models import User, CoverLetter, Resume, ParsedResume, Job, JobDescription
from app.services.cover_letter_generator import CoverLetterGenerator

router = APIRouter()


class GenerateRequest(BaseModel):
    resume_id: str
    job_id: str
    tone: str = "professional"
    additional_context: str = ""
    save: bool = True


@router.post("/generate")
async def generate_cover_letter(
    request: Request,
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a tailored cover letter for a resume-job pair."""
    # Load resume
    resume_result = await db.execute(
        select(Resume).where(Resume.id == uuid.UUID(body.resume_id), Resume.user_id == current_user.id)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    parsed_result = await db.execute(
        select(ParsedResume).where(ParsedResume.resume_id == resume.id)
    )
    parsed = parsed_result.scalar_one_or_none()
    if not parsed:
        raise HTTPException(status_code=409, detail="Resume not yet parsed. Try again shortly.")

    # Load job
    job_result = await db.execute(select(Job).where(Job.id == uuid.UUID(body.job_id)))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Load job description separately
    job_desc_result = await db.execute(
        select(JobDescription).where(JobDescription.job_id == job.id)
    )
    job_desc = job_desc_result.scalar_one_or_none()

    resume_data = {
        "full_name": parsed.full_name,
        "skills": parsed.skills or {},
        "experience": parsed.experience or [],
        "total_years_experience": parsed.total_years_experience or 0,
    }
    job_data = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "required_skills": (job_desc.required_skills if job_desc else []) or [],
    }

    # Read optional LLM override from request headers (set by frontend Settings)
    llm_provider = request.headers.get("x-llm-provider")
    llm_api_key = request.headers.get("x-llm-api-key")
    llm_model = request.headers.get("x-llm-model")

    generator = CoverLetterGenerator()
    try:
        content = await generator.generate(
            resume_data=resume_data,
            job_data=job_data,
            tone=body.tone,
            additional_context=body.additional_context,
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
        )
    except ValueError as e:
        # Config error (e.g., missing API key)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # LLM or network error — surface the real message
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {type(e).__name__}: {str(e)}"
        )

    cover_letter_record = None
    if body.save:
        try:
            cl = CoverLetter(
                user_id=current_user.id,
                title=f"Cover Letter — {job.title} at {job.company}",
                content=content,
                tone=body.tone,
                word_count=len(content.split()),
                is_ai_generated=True,
                llm_model_used=llm_provider or "groq",
            )
            db.add(cl)
            await db.commit()
            await db.refresh(cl)
            cover_letter_record = str(cl.id)
        except Exception as e:
            # Don't fail the whole request if saving fails — return content anyway
            import structlog
            log = structlog.get_logger(__name__)
            log.warning("Failed to save cover letter record", error=str(e))

    return {
        "content": content,
        "word_count": len(content.split()),
        "tone": body.tone,
        "cover_letter_id": cover_letter_record,
    }



@router.get("/")
async def list_cover_letters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all saved cover letters."""
    result = await db.execute(
        select(CoverLetter)
        .where(CoverLetter.user_id == current_user.id)
        .order_by(CoverLetter.created_at.desc())
        .limit(50)
    )
    letters = result.scalars().all()
    return {
        "items": [
            {
                "id": str(cl.id),
                "title": cl.title,
                "tone": cl.tone,
                "word_count": cl.word_count,
                "is_ai_generated": cl.is_ai_generated,
                "created_at": cl.created_at.isoformat(),
            }
            for cl in letters
        ],
        "total": len(letters),
    }
