"""Users profile management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get authenticated user's full profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "headline": current_user.headline,
        "bio": current_user.bio,
        "location": current_user.location,
        "linkedin_url": current_user.linkedin_url,
        "github_url": current_user.github_url,
        "portfolio_url": current_user.portfolio_url,
        "avatar_url": current_user.avatar_url,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }


@router.patch("/me")
async def update_profile(
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update authenticated user's profile."""
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return {"message": "Profile updated successfully", "updated_fields": list(update_data.keys())}
