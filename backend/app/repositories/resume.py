from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.resume import Resume, ParsedResume


class ResumeRepository(BaseRepository[Resume]):
    """Repository for Resume model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Resume, db)

    async def get_by_user_id(self, user_id: UUID) -> List[Resume]:
        """Fetch all resumes belonging to a user, ordered by creation time."""
        result = await self.db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_primary(self, user_id: UUID) -> Optional[Resume]:
        """Fetch the primary resume for a user."""
        result = await self.db.execute(
            select(Resume).where(
                Resume.user_id == user_id,
                Resume.is_primary == True,
            )
        )
        return result.scalar_one_or_none()


class ParsedResumeRepository(BaseRepository[ParsedResume]):
    """Repository for ParsedResume model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ParsedResume, db)

    async def get_by_resume_id(self, resume_id: UUID) -> Optional[ParsedResume]:
        """Fetch parsed resume information for a given resume UUID."""
        result = await self.db.execute(
            select(ParsedResume).where(ParsedResume.resume_id == resume_id)
        )
        return result.scalar_one_or_none()
