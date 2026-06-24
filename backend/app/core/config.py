"""
ResuMesh Application Configuration
All settings loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "ResuMesh"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # ── Backend ─────────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 4

    ALLOWED_ORIGINS: Any = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://resumesh_user:resumesh_password@localhost:5432/resumesh"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_RESUMES: str = "resumesh_resumes"
    CHROMA_COLLECTION_JOBS: str = "resumesh_jobs"

    # ── MLflow ──────────────────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "resumesh-matching"

    # ── LLM ─────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "ollama"  # ollama | groq | gemini
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # ── Sentence Transformers ────────────────────────────────────────────────
    SENTENCE_TRANSFORMER_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── File Storage ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: Any = ["pdf", "docx"]

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
