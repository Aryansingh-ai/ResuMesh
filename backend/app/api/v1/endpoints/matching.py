"""
Matching endpoints — compute resume-to-job match scores.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.resume import Resume, ParsedResume
from app.models.job import Job, JobDescription
from app.models.application import Application
from app.services.matching_engine import MatchingEngine
from app.services.embedding_service import get_embedding_service

router = APIRouter()
logger = structlog.get_logger(__name__)


class MatchRequest(BaseModel):
    resume_id: str
    job_id: str
    save_to_application: bool = True


@router.post("/score")
async def compute_match_score(
    body: MatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compute the match score between a resume and a job.
    Optionally saves result to an Application record.
    """
    # Load resume
    resume_result = await db.execute(
        select(Resume).where(
            Resume.id == uuid.UUID(body.resume_id),
            Resume.user_id == current_user.id,
        )
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    parsed_result = await db.execute(
        select(ParsedResume).where(ParsedResume.resume_id == resume.id)
    )
    parsed_resume = parsed_result.scalar_one_or_none()
    if not parsed_resume:
        raise HTTPException(
            status_code=409,
            detail="Resume has not been parsed yet. Please wait and try again.",
        )

    # Load job
    job_result = await db.execute(select(Job).where(Job.id == uuid.UUID(body.job_id)))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    desc_result = await db.execute(
        select(JobDescription).where(JobDescription.job_id == job.id)
    )
    job_description = desc_result.scalar_one_or_none()

    # Build data dicts
    parsed_resume_dict = {
        "full_name": parsed_resume.full_name,
        "skills": parsed_resume.skills or {},
        "experience": parsed_resume.experience or [],
        "education": parsed_resume.education or [],
        "total_years_experience": parsed_resume.total_years_experience or 0,
        "raw_text": parsed_resume.raw_text or "",
    }

    job_desc_dict = {}
    if job_description:
        job_desc_dict = {
            "required_skills": job_description.required_skills or [],
            "preferred_skills": job_description.preferred_skills or [],
            "responsibilities": job_description.responsibilities or [],
            "education_requirements": job_description.education_requirements or [],
            "min_years_experience": job_description.min_years_experience,
            "max_years_experience": job_description.max_years_experience,
        }

    # Run matching
    embedding_service = get_embedding_service()
    engine = MatchingEngine(embedding_service=embedding_service)

    match_result = await engine.match(
        parsed_resume=parsed_resume_dict,
        job_description=job_desc_dict,
        raw_resume_text=parsed_resume.raw_text or "",
        raw_job_text=job.raw_description or "",
        use_embeddings=True,
    )

    # Optionally save to application
    application_id = None
    if body.save_to_application:
        # Check if application already exists
        app_result = await db.execute(
            select(Application).where(
                Application.user_id == current_user.id,
                Application.job_id == job.id,
            )
        )
        application = app_result.scalar_one_or_none()

        if application:
            # Update existing
            application.match_score = match_result.score
            application.matched_skills = match_result.matched_skills
            application.missing_skills = match_result.missing_skills
            application.recommendations = [r for r in match_result.recommendations]
            application.resume_id = resume.id
        else:
            # Create new application in 'saved' state
            application = Application(
                user_id=current_user.id,
                job_id=job.id,
                resume_id=resume.id,
                status="saved",
                match_score=match_result.score,
                matched_skills=match_result.matched_skills,
                missing_skills=match_result.missing_skills,
                recommendations=[r for r in match_result.recommendations],
            )
            db.add(application)

        await db.commit()
        await db.refresh(application)
        application_id = str(application.id)

    logger.info(
        "Match computed",
        user_id=str(current_user.id),
        resume_id=body.resume_id,
        job_id=body.job_id,
        score=match_result.score,
    )

    return {
        "score": match_result.score,
        "matched_skills": match_result.matched_skills,
        "missing_skills": match_result.missing_skills,
        "recommendations": match_result.recommendations,
        "details": match_result.details,
        "model_version": match_result.model_version,
        "resume_id": body.resume_id,
        "job_id": body.job_id,
        "application_id": application_id,
    }


@router.post("/quick-score")
async def quick_match_score(
    resume_text: str,
    job_text: str,
    current_user: User = Depends(get_current_user),
):
    """
    Quick match score computation from raw text (no DB persistence).
    Useful for the Chrome extension.
    """
    from app.services.resume_parser import ResumeParser
    from app.services.job_extractor import JobDescriptionExtractor

    # Parse on the fly
    parser = ResumeParser()
    parsed_resume = parser._parse_text(resume_text)

    extractor = JobDescriptionExtractor()
    job_desc = extractor.extract(job_text)

    embedding_service = get_embedding_service()
    engine = MatchingEngine(embedding_service=embedding_service)

    result = await engine.match(
        parsed_resume=parsed_resume,
        job_description=job_desc,
        raw_resume_text=resume_text,
        raw_job_text=job_text,
        use_embeddings=True,
    )

    return {
        "score": result.score,
        "matched_skills": result.matched_skills[:10],
        "missing_skills": result.missing_skills[:10],
        "recommendations": result.recommendations[:3],
        "model_version": result.model_version,
    }
