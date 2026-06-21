"""User service — data access layer for user operations."""

from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User


class UserService:
    """Data access service for User model operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID string."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            return result.scalar_one_or_none()
        except (ValueError, AttributeError):
            return None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
