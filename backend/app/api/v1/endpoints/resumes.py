"""
Resume endpoints — upload, list, parse, delete.
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File,
    status, BackgroundTasks, Form,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.metrics import resume_uploads_total
from app.models.user import User
from app.models.resume import Resume, ParsedResume
from app.services.resume_parser import ResumeParser
from app.services.embedding_service import EmbeddingService, get_embedding_service

router = APIRouter()
logger = structlog.get_logger(__name__)


async def _process_resume_background(
    resume_id: str,
    file_path: str,
    file_type: str,
    user_id: str,
) -> None:
    """Background task: parse resume and index embeddings."""
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            parser = ResumeParser()
            parsed_data = parser.parse(file_path, file_type)

            resume_result = await db.execute(
                select(Resume).where(Resume.id == uuid.UUID(resume_id))
            )
            resume = resume_result.scalar_one_or_none()
            if not resume:
                return

            # Save parsed data
            parsed_resume = ParsedResume(
                resume_id=resume.id,
                **{k: v for k, v in parsed_data.items() if k != "raw_text"},
                raw_text=parsed_data.get("raw_text"),
            )
            db.add(parsed_resume)
            resume.is_parsed = True

            # Index in ChromaDB
            try:
                embedding_service = get_embedding_service()
                if embedding_service._model:
                    doc_id = await embedding_service.index_resume(
                        doc_id=resume_id,
                        text=parsed_data.get("raw_text", ""),
                        metadata={"user_id": user_id, "resume_id": resume_id},
                    )
                    resume.chroma_doc_id = doc_id
            except Exception as e:
                logger.warning("Failed to index resume embedding", error=str(e))

            await db.commit()
            logger.info("Resume background processing complete", resume_id=resume_id)

        except Exception as e:
            logger.error("Resume background processing failed", resume_id=resume_id, error=str(e))


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    is_primary: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and parse a resume (PDF or DOCX)."""
    # Validate file type
    file_ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read and validate file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {size_mb:.1f}MB exceeds limit of {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = upload_dir / unique_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # If setting as primary, unset current primary
    if is_primary:
        primary_result = await db.execute(
            select(Resume).where(
                Resume.user_id == current_user.id,
                Resume.is_primary == True,
            )
        )
        for r in primary_result.scalars().all():
            r.is_primary = False

    # Create Resume record
    resume = Resume(
        user_id=current_user.id,
        title=title.strip(),
        file_name=file.filename or unique_filename,
        file_path=str(file_path),
        file_type=file_ext,
        file_size_bytes=len(content),
        is_primary=is_primary,
    )
    db.add(resume)
    await db.flush()

    # Queue background processing
    background_tasks.add_task(
        _process_resume_background,
        str(resume.id),
        str(file_path),
        file_ext,
        str(current_user.id),
    )

    await db.commit()
    await db.refresh(resume)

    resume_uploads_total.labels(status="success").inc()
    logger.info("Resume uploaded", resume_id=str(resume.id), user_id=str(current_user.id))

    return {
        "id": str(resume.id),
        "title": resume.title,
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "file_size_bytes": resume.file_size_bytes,
        "is_primary": resume.is_primary,
        "is_parsed": resume.is_parsed,
        "created_at": resume.created_at.isoformat(),
        "message": "Resume uploaded successfully. Parsing in progress...",
    }


@router.get("/")
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all resumes for the authenticated user."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "file_name": r.file_name,
                "file_type": r.file_type,
                "file_size_bytes": r.file_size_bytes,
                "is_primary": r.is_primary,
                "is_parsed": r.is_parsed,
                "created_at": r.created_at.isoformat(),
            }
            for r in resumes
        ],
        "total": len(resumes),
    }


@router.get("/{resume_id}")
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific resume including parsed data."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == uuid.UUID(resume_id),
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    parsed_result = await db.execute(
        select(ParsedResume).where(ParsedResume.resume_id == resume.id)
    )
    parsed = parsed_result.scalar_one_or_none()

    response = {
        "id": str(resume.id),
        "title": resume.title,
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "is_primary": resume.is_primary,
        "is_parsed": resume.is_parsed,
        "created_at": resume.created_at.isoformat(),
        "parsed_data": None,
    }

    if parsed:
        response["parsed_data"] = {
            "full_name": parsed.full_name,
            "email": parsed.email,
            "phone": parsed.phone,
            "location": parsed.location,
            "linkedin_url": parsed.linkedin_url,
            "github_url": parsed.github_url,
            "skills": parsed.skills,
            "experience": parsed.experience,
            "education": parsed.education,
            "projects": parsed.projects,
            "certifications": parsed.certifications,
            "languages": parsed.languages,
            "total_years_experience": parsed.total_years_experience,
            "seniority_level": parsed.seniority_level,
        }

    return response


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a resume and its file."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == uuid.UUID(resume_id),
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Delete file
    try:
        file_path = Path(resume.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning("Failed to delete resume file", error=str(e))

    await db.delete(resume)
    await db.commit()
    logger.info("Resume deleted", resume_id=resume_id, user_id=str(current_user.id))
