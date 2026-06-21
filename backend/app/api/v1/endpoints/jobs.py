"""
Job analysis endpoints — submit job descriptions from extension or frontend.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.metrics import job_analyses_total
from app.models.user import User
from app.models.job import Job, JobDescription
from app.services.job_extractor import JobDescriptionExtractor
from app.services.embedding_service import get_embedding_service

router = APIRouter()
logger = structlog.get_logger(__name__)


class JobAnalyzeRequest(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    portal: str = "manual"
    portal_job_id: Optional[str] = None
    job_url: Optional[str] = None
    raw_description: str


class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str]
    portal: str
    job_url: Optional[str]
    required_skills: Optional[list]
    preferred_skills: Optional[list]
    tech_stack: Optional[list]
    min_years_experience: Optional[float]
    created_at: str


async def _index_job_background(job_id: str, text: str) -> None:
    """Background task: index job in ChromaDB."""
    try:
        embedding_service = get_embedding_service()
        if embedding_service._model:
            await embedding_service.index_job(
                doc_id=job_id,
                text=text,
                metadata={"job_id": job_id},
            )
    except Exception as e:
        logger.warning("Failed to index job embedding", job_id=job_id, error=str(e))


@router.post("/analyze", status_code=status.HTTP_201_CREATED)
async def analyze_job(
    body: JobAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a job description for analysis.
    Extracts skills, requirements, and stores in DB.
    """
    if len(body.raw_description.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description is too short (minimum 50 characters).",
        )

    # Create Job record
    job = Job(
        title=body.title.strip(),
        company=body.company.strip(),
        location=body.location,
        job_type=body.job_type,
        portal=body.portal,
        portal_job_id=body.portal_job_id,
        job_url=body.job_url,
        raw_description=body.raw_description,
    )
    db.add(job)
    await db.flush()

    # Extract structured data
    extractor = JobDescriptionExtractor()
    try:
        extracted = extractor.extract(body.raw_description)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    description = JobDescription(
        job_id=job.id,
        required_skills=extracted.get("required_skills"),
        preferred_skills=extracted.get("preferred_skills"),
        tech_stack=extracted.get("tech_stack"),
        soft_skills=extracted.get("soft_skills"),
        responsibilities=extracted.get("responsibilities"),
        qualifications=extracted.get("qualifications"),
        education_requirements=extracted.get("education_requirements"),
        certifications=extracted.get("certifications"),
        min_years_experience=extracted.get("min_years_experience"),
        max_years_experience=extracted.get("max_years_experience"),
    )
    db.add(description)

    await db.commit()
    await db.refresh(job)

    # Background: index in ChromaDB
    background_tasks.add_task(_index_job_background, str(job.id), body.raw_description)

    job_analyses_total.labels(portal=body.portal, status="success").inc()
    logger.info("Job analyzed", job_id=str(job.id), portal=body.portal)

    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "portal": job.portal,
        "job_url": job.job_url,
        "required_skills": extracted.get("required_skills", []),
        "preferred_skills": extracted.get("preferred_skills", []),
        "tech_stack": extracted.get("tech_stack", []),
        "min_years_experience": extracted.get("min_years_experience"),
        "responsibilities": extracted.get("responsibilities", [])[:5],
        "created_at": job.created_at.isoformat(),
        "message": "Job analyzed successfully",
    }


@router.get("/")
async def list_jobs(
    portal: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List analyzed jobs with optional portal filter."""
    query = select(Job).order_by(Job.created_at.desc()).offset(skip).limit(min(limit, 100))
    if portal:
        query = query.where(Job.portal == portal)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(j.id),
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "portal": j.portal,
                "job_url": j.job_url,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ],
        "total": len(jobs),
        "skip": skip,
        "limit": limit,
    }


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific job."""
    result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    desc_result = await db.execute(
        select(JobDescription).where(JobDescription.job_id == job.id)
    )
    description = desc_result.scalar_one_or_none()

    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "job_type": job.job_type,
        "portal": job.portal,
        "job_url": job.job_url,
        "raw_description": job.raw_description,
        "created_at": job.created_at.isoformat(),
        "description": {
            "required_skills": description.required_skills,
            "preferred_skills": description.preferred_skills,
            "tech_stack": description.tech_stack,
            "soft_skills": description.soft_skills,
            "responsibilities": description.responsibilities,
            "qualifications": description.qualifications,
            "education_requirements": description.education_requirements,
            "certifications": description.certifications,
            "min_years_experience": description.min_years_experience,
            "max_years_experience": description.max_years_experience,
        } if description else None,
    }
