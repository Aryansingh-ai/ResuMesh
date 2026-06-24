from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.job import Job, JobDescription


class JobRepository(BaseRepository[Job]):
    """Repository for Job model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Job, db)

    async def get_by_company(self, company: str) -> List[Job]:
        """Fetch jobs by company name (case-insensitive)."""
        result = await self.db.execute(
            select(Job).where(Job.company.ilike(company))
        )
        return list(result.scalars().all())

    async def get_by_portal_job_id(self, portal: str, portal_job_id: str) -> Optional[Job]:
        """Fetch job by source portal and portal-specific job ID."""
        result = await self.db.execute(
            select(Job).where(
                Job.portal == portal,
                Job.portal_job_id == portal_job_id,
            )
        )
        return result.scalar_one_or_none()


class JobDescriptionRepository(BaseRepository[JobDescription]):
    """Repository for JobDescription model database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(JobDescription, db)

    async def get_by_job_id(self, job_id: UUID) -> Optional[JobDescription]:
        """Fetch job description details for a given job UUID."""
        result = await self.db.execute(
            select(JobDescription).where(JobDescription.job_id == job_id)
        )
        return result.scalar_one_or_none()
