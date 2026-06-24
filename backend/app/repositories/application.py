from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.application import Application


class ApplicationRepository(BaseRepository[Application]):
    """Repository for Application model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Application, db)

    async def get_by_user_id(self, user_id: UUID) -> List[Application]:
        """Fetch all job applications for a user, ordered by creation time."""
        result = await self.db.execute(
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(Application.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(self, user_id: UUID, status: str) -> List[Application]:
        """Fetch job applications filtered by status for a specific user."""
        result = await self.db.execute(
            select(Application)
            .where(
                Application.user_id == user_id,
                Application.status == status,
            )
            .order_by(Application.created_at.desc())
        )
        return list(result.scalars().all())
