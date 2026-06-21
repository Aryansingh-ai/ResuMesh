"""Admin-only endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.application import Application
from app.models.cover_letter import AuditLog

router = APIRouter()


@router.get("/stats")
async def admin_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """System-wide statistics for admins."""
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    resume_count = (await db.execute(select(func.count(Resume.id)))).scalar()
    job_count = (await db.execute(select(func.count(Job.id)))).scalar()
    app_count = (await db.execute(select(func.count(Application.id)))).scalar()

    return {
        "users": {"total": user_count},
        "resumes": {"total": resume_count},
        "jobs": {"total": job_count},
        "applications": {"total": app_count},
    }


@router.get("/users")
async def admin_list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """List all users (admin only)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": len(users),
    }
