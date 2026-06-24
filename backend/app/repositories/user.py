from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for User model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email address (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
