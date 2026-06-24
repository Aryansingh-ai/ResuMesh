from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.resume import ResumeRepository as LegacyResumeRepository
from app.models.postgres_models import Resume, ParsedResume, Embedding

class ResumeRepository(LegacyResumeRepository):
    """Repository for Resume model PostgreSQL operations."""
    
    async def get_embeddings(self, resume_id: UUID) -> Optional[List[float]]:
        """Retrieve embedding vector for a resume."""
        result = await self.db.execute(
            select(Embedding.embedding).where(Embedding.resume_id == resume_id)
        )
        row = result.fetchone()
        return list(row[0]) if row else None
