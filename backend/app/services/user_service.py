"""User service — data access layer for user operations."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository


class UserService:
    """Service layer for User model operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserRepository(db)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID string."""
        return await self.repository.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return await self.repository.get_by_email(email)
