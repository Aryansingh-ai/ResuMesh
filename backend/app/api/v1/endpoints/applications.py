"""Applications tracker endpoints."""

import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.application import Application
from app.models.job import Job

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    offer_amount: Optional[str] = None


@router.get("/")
async def list_applications(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all applications with optional status filter."""
    query = (
        select(Application, Job)
        .join(Job, Application.job_id == Job.id, isouter=True)
        .where(Application.user_id == current_user.id)
        .order_by(Application.updated_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
    )
    if status_filter:
        query = query.where(Application.status == status_filter)

    result = await db.execute(query)
    rows = result.all()

    return {
        "items": [
            {
                "id": str(app.id),
                "status": app.status,
                "match_score": app.match_score,
                "matched_skills": app.matched_skills,
                "missing_skills": app.missing_skills,
                "notes": app.notes,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat(),
                "job": {
                    "id": str(job.id),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "portal": job.portal,
                    "job_url": job.job_url,
                } if job else None,
            }
            for app, job in rows
        ],
        "total": len(rows),
        "skip": skip,
        "limit": limit,
    }


@router.patch("/{application_id}/status")
async def update_application_status(
    application_id: str,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the status of an application."""
    valid_statuses = {"saved", "applied", "interview", "rejected", "offer", "accepted"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {valid_statuses}")

    result = await db.execute(
        select(Application).where(
            Application.id == uuid.UUID(application_id),
            Application.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = body.status
    if body.notes is not None:
        application.notes = body.notes
    if body.interview_date:
        application.interview_date = body.interview_date
    if body.offer_amount:
        application.offer_amount = body.offer_amount
    if body.status == "applied" and not application.applied_at:
        application.applied_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(application)

    return {
        "id": str(application.id),
        "status": application.status,
        "updated_at": application.updated_at.isoformat(),
    }


@router.get("/stats/summary")
async def application_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get application pipeline statistics."""
    result = await db.execute(
        select(Application.status, func.count(Application.id).label("count"))
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    )
    rows = result.all()
    stats = {row.status: row.count for row in rows}

    # Score stats
    score_result = await db.execute(
        select(
            func.avg(Application.match_score).label("avg_score"),
            func.max(Application.match_score).label("max_score"),
            func.count(Application.id).label("total"),
        ).where(Application.user_id == current_user.id)
    )
    score_row = score_result.one()

    return {
        "by_status": stats,
        "total": int(score_row.total or 0),
        "avg_match_score": round(float(score_row.avg_score or 0), 1),
        "max_match_score": round(float(score_row.max_score or 0), 1),
    }
