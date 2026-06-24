from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.job import JobRepository as LegacyJobRepository
from app.models.postgres_models import Job, JobDescription

class JobRepository(LegacyJobRepository):
    """Repository for Job model PostgreSQL operations."""
    
    async def get_embedding(self, job_id: UUID) -> Optional[List[float]]:
        """Retrieve embedding vector for a job."""
        result = await self.db.execute(
            select(Job.embedding).where(Job.id == job_id)
        )
        row = result.fetchone()
        return list(row[0]) if row else None
