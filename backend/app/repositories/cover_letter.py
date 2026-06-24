from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.cover_letter import CoverLetter, Feedback, Recommendation, AuditLog


class CoverLetterRepository(BaseRepository[CoverLetter]):
    """Repository for CoverLetter model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(CoverLetter, db)

    async def get_by_user_id(self, user_id: UUID) -> List[CoverLetter]:
        """Fetch all cover letters for a user, ordered by creation time."""
        result = await self.db.execute(
            select(CoverLetter)
            .where(CoverLetter.user_id == user_id)
            .order_by(CoverLetter.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_application_id(self, application_id: UUID) -> List[CoverLetter]:
        """Fetch cover letters generated for a specific job application."""
        result = await self.db.execute(
            select(CoverLetter).where(CoverLetter.application_id == application_id)
        )
        return list(result.scalars().all())


class FeedbackRepository(BaseRepository[Feedback]):
    """Repository for Feedback model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Feedback, db)

    async def get_by_user_id(self, user_id: UUID) -> List[Feedback]:
        """Fetch all feedback submissions by a user."""
        result = await self.db.execute(
            select(Feedback)
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
        )
        return list(result.scalars().all())


class RecommendationRepository(BaseRepository[Recommendation]):
    """Repository for Recommendation model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Recommendation, db)

    async def get_by_user_id(self, user_id: UUID) -> List[Recommendation]:
        """Fetch all recommendations for a user."""
        result = await self.db.execute(
            select(Recommendation)
            .where(Recommendation.user_id == user_id)
            .order_by(Recommendation.priority.asc(), Recommendation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active(self, user_id: UUID) -> List[Recommendation]:
        """Fetch recommendations for a user that are active (not dismissed or completed)."""
        result = await self.db.execute(
            select(Recommendation)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.is_dismissed == False,
                Recommendation.is_completed == False,
            )
            .order_by(Recommendation.priority.asc(), Recommendation.created_at.desc())
        )
        return list(result.scalars().all())


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def get_by_user_id(self, user_id: UUID, limit: int = 100) -> List[AuditLog]:
        """Fetch audit logs for a user, ordered by creation time."""
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
