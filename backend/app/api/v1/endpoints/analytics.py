"""Analytics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.application import Application
from app.models.resume import Resume
from app.models.job import Job
from app.models.cover_letter import CoverLetter, Feedback

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard analytics for the authenticated user."""
    # Applications by status
    app_result = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    )
    apps_by_status = {row[0]: row[1] for row in app_result.all()}

    # Average match score
    score_result = await db.execute(
        select(func.avg(Application.match_score), func.count(Application.id))
        .where(Application.user_id == current_user.id)
    )
    avg_score, total_apps = score_result.one()

    # Resume count
    resume_count = await db.execute(
        select(func.count(Resume.id)).where(Resume.user_id == current_user.id)
    )

    # Cover letter count
    cl_count = await db.execute(
        select(func.count(CoverLetter.id)).where(CoverLetter.user_id == current_user.id)
    )

    # Top missing skills
    missing_skills_result = await db.execute(
        select(Application.missing_skills)
        .where(
            Application.user_id == current_user.id,
            Application.missing_skills.isnot(None),
        )
        .limit(20)
    )
    skill_frequency: dict = {}
    for row in missing_skills_result.scalars().all():
        for skill in (row or []):
            skill_frequency[skill] = skill_frequency.get(skill, 0) + 1

    top_missing = sorted(skill_frequency.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "applications": {
            "total": int(total_apps or 0),
            "by_status": apps_by_status,
            "avg_match_score": round(float(avg_score or 0), 1),
        },
        "resumes": {"total": resume_count.scalar() or 0},
        "cover_letters": {"total": cl_count.scalar() or 0},
        "top_missing_skills": [{"skill": s, "frequency": f} for s, f in top_missing],
    }
