"""
Embedding Service — Sentence Transformers + ChromaDB vector storage and retrieval.
"""

import asyncio
from functools import lru_cache
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    Manages text embeddings using Sentence Transformers.
    Stores and retrieves vectors from ChromaDB.
    """

    _instance: Optional["EmbeddingService"] = None

    def __init__(self):
        self._model: Optional[SentenceTransformer] = None
        self._chroma_client: Optional[chromadb.HttpClient] = None
        self._resume_collection = None
        self._job_collection = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self) -> None:
        """Initialize model and ChromaDB connection."""
        loop = asyncio.get_event_loop()

        # Load model in thread pool (blocking operation)
        logger.info("Loading sentence transformer model", model=settings.SENTENCE_TRANSFORMER_MODEL)
        self._model = await loop.run_in_executor(
            None, SentenceTransformer, settings.SENTENCE_TRANSFORMER_MODEL
        )
        logger.info("Sentence transformer model loaded")

        # Connect to ChromaDB
        self._chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )

        # Get or create collections
        self._resume_collection = self._chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_RESUMES,
            metadata={"hnsw:space": "cosine"},
        )
        self._job_collection = self._chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_JOBS,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collections initialized")

    def _encode(self, text: str) -> List[float]:
        """Synchronously encode text to embedding vector."""
        if self._model is None:
            raise RuntimeError("EmbeddingService not initialized. Call initialize() first.")
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    async def encode(self, text: str) -> List[float]:
        """Asynchronously encode text to embedding vector."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode, text)

    async def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.
        Returns a float in range [0, 1].
        """
        loop = asyncio.get_event_loop()

        def _compute():
            emb1 = np.array(self._encode(text1))
            emb2 = np.array(self._encode(text2))
            # Cosine similarity (vectors are already normalized)
            return float(np.dot(emb1, emb2))

        similarity = await loop.run_in_executor(None, _compute)
        return max(0.0, min(1.0, similarity))

    async def index_resume(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> str:
        """
        Index a resume in ChromaDB.

        Args:
            doc_id: Unique document identifier.
            text: Resume text to embed.
            metadata: Additional metadata to store.

        Returns:
            The document ID.
        """
        embedding = await self.encode(text)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._resume_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text[:10000]],  # ChromaDB document limit
                metadatas=[{k: str(v) for k, v in metadata.items() if v is not None}],
            ),
        )
        logger.info("Resume indexed in ChromaDB", doc_id=doc_id)
        return doc_id

    async def index_job(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> str:
        """Index a job description in ChromaDB."""
        embedding = await self.encode(text)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._job_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text[:10000]],
                metadatas=[{k: str(v) for k, v in metadata.items() if v is not None}],
            ),
        )
        logger.info("Job indexed in ChromaDB", doc_id=doc_id)
        return doc_id

    async def find_similar_resumes(
        self, query_text: str, n_results: int = 5, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find similar resumes to a query text."""
        embedding = await self.encode(query_text)
        where = {"user_id": user_id} if user_id else None

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._resume_collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, 10),
                where=where,
            ),
        )

        items = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                items.append({
                    "doc_id": doc_id,
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                    "document": results["documents"][0][i] if results.get("documents") else None,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                })
        return items

    async def find_similar_jobs(
        self, query_text: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar job descriptions to a query text."""
        embedding = await self.encode(query_text)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._job_collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, 10),
            ),
        )

        items = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                items.append({
                    "doc_id": doc_id,
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                    "document": results["documents"][0][i] if results.get("documents") else None,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                })
        return items

    async def delete_document(self, collection_type: str, doc_id: str) -> None:
        """Delete a document from ChromaDB."""
        collection = (
            self._resume_collection if collection_type == "resume" else self._job_collection
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: collection.delete(ids=[doc_id]))
        logger.info("Document deleted from ChromaDB", doc_id=doc_id, collection=collection_type)


# Singleton accessor
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService.get_instance()
