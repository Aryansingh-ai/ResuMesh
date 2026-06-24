import asyncio
import uuid
import hashlib
from typing import List, Dict, Any, Optional
import structlog
import numpy as np

from app.core.config import settings

logger = structlog.get_logger(__name__)

class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None

    def __init__(self):
        self._model = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self) -> None:
        """Initialize sentence-transformers model (mocked for offline compatibility)."""
        logger.info("Mock loading sentence transformer model", model=settings.SENTENCE_TRANSFORMER_MODEL)
        self._model = "MOCK_MODEL"
        logger.info("Sentence transformer model mock-loaded successfully")

    def _encode(self, text: str) -> List[float]:
        """Synchronously encode text to embedding vector (Mock)."""
        if self._model is None:
            raise RuntimeError("EmbeddingService not initialized. Call initialize() first.")
        # Generate a deterministic vector based on text
        h = hashlib.sha256(text.encode('utf-8')).digest()
        vec = []
        for i in range(384):
            val = (h[i % 32] + i) % 256
            vec.append(float(val - 128))
        norm = sum(x**2 for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def encode(self, text: str) -> List[float]:
        """Asynchronously encode text to embedding vector."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode, text)

    async def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts (vectors are normalized)."""
        emb1 = np.array(self._encode(text1))
        emb2 = np.array(self._encode(text2))
        similarity = float(np.dot(emb1, emb2))
        return max(0.0, min(1.0, similarity))

    # --- Target Architecture Functions ---
    def generate_text_embedding(self, text: str) -> List[float]:
        return self._encode(text)

    def generate_resume_embedding(self, text: str) -> List[float]:
        return self._encode(text)

    def generate_job_embedding(self, text: str) -> List[float]:
        return self._encode(text)

    # --- Database / Vector DB Compatibility Layer ---
    async def index_resume(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> str:
        """Store resume embedding in PostgreSQL pgvector embeddings table."""
        embedding = await self.encode(text)
        from app.core.database import AsyncSessionLocal
        from app.models.postgres_models import Embedding
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            resume_uuid = uuid.UUID(doc_id)
            result = await session.execute(
                select(Embedding).where(Embedding.resume_id == resume_uuid)
            )
            record = result.scalar_one_or_none()
            if record:
                record.embedding = embedding
            else:
                record = Embedding(
                    resume_id=resume_uuid,
                    embedding=embedding
                )
                session.add(record)
            await session.commit()
            
        logger.info("Resume indexed in Supabase PostgreSQL (pgvector)", doc_id=doc_id)
        return doc_id

    async def index_job(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> str:
        """Store job embedding directly inside PostgreSQL jobs table."""
        embedding = await self.encode(text)
        from app.core.database import AsyncSessionLocal
        from app.models.postgres_models import Job
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            job_uuid = uuid.UUID(doc_id)
            result = await session.execute(
                select(Job).where(Job.id == job_uuid)
            )
            record = result.scalar_one_or_none()
            if record:
                record.embedding = embedding
                if not record.description:
                    record.description = text
            await session.commit()
            
        logger.info("Job indexed in Supabase PostgreSQL (pgvector)", doc_id=doc_id)
        return doc_id

    async def delete_document(self, collection_type: str, doc_id: str) -> None:
        """Delete embedding from PostgreSQL table."""
        from app.core.database import AsyncSessionLocal
        from app.models.postgres_models import Embedding, Job
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            doc_uuid = uuid.UUID(doc_id)
            if collection_type == "resume":
                result = await session.execute(
                    select(Embedding).where(Embedding.resume_id == doc_uuid)
                )
                record = result.scalar_one_or_none()
                if record:
                    await session.delete(record)
            elif collection_type == "job":
                result = await session.execute(
                    select(Job).where(Job.id == doc_uuid)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.embedding = None
            await session.commit()
            
        logger.info("Document deleted from pgvector storage", doc_id=doc_id, collection=collection_type)

def get_embedding_service() -> EmbeddingService:
    return EmbeddingService.get_instance()
