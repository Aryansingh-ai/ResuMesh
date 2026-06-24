"""
Resume endpoints — upload to Supabase Storage, list, parse, delete.
"""

import os
import uuid
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File,
    status, BackgroundTasks, Form,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.metrics import resume_uploads_total
from app.models.postgres_models import User, Resume, ParsedResume
from app.services.resume_parser import ResumeParser
from app.services.embedding_service import get_embedding_service
from app.services.supabase_storage import get_storage_service

router = APIRouter()
logger = structlog.get_logger(__name__)


async def _process_resume_background(
    resume_id: str,
    storage_path: str,
    file_type: str,
    user_id: str,
) -> None:
    """Background task: download file from Supabase, parse and index embeddings in pgvector."""
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        temp_path = None
        try:
            # Download file content from Supabase Storage
            storage_service = get_storage_service()
            content = await storage_service.download_file("resumes", storage_path)

            # Write to a temp file for PyMuPDF/docx parsing compatibility
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tf:
                tf.write(content)
                temp_path = tf.name

            parser = ResumeParser()
            parsed_data = parser.parse(temp_path, file_type)

            resume_result = await db.execute(
                select(Resume).where(Resume.id == uuid.UUID(resume_id))
            )
            resume = resume_result.scalar_one_or_none()
            if not resume:
                return

            # Save parsed data
            parsed_resume = ParsedResume(
                resume_id=resume.id,
                name=parsed_data.get("full_name"),
                email=parsed_data.get("email"),
                phone=parsed_data.get("phone"),
                skills=parsed_data.get("skills", {}),
                education=parsed_data.get("education", []),
                experience=parsed_data.get("experience", []),
                projects=parsed_data.get("projects", []),
                parsed_json=parsed_data,
                raw_text=parsed_data.get("raw_text"),
                full_name=parsed_data.get("full_name"),
            )
            db.add(parsed_resume)
            resume.is_parsed = True

            # Generate and index embedding in pgvector
            try:
                embedding_service = get_embedding_service()
                await embedding_service.index_resume(
                    doc_id=resume_id,
                    text=parsed_data.get("raw_text", ""),
                    metadata={"user_id": user_id, "resume_id": resume_id},
                )
            except Exception as e:
                logger.warning("Failed to index resume embedding in pgvector", error=str(e))

            await db.commit()
            logger.info("Resume background processing complete", resume_id=resume_id)

        except Exception as e:
            logger.error("Resume background processing failed", resume_id=resume_id, error=str(e))
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    is_primary: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload resume to Supabase Storage and trigger background parser."""
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

    # Compute SHA256 hash of file content
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for existing active (not soft-deleted) resume for current user with identical hash
    dup_result = await db.execute(
        select(Resume).where(
            Resume.user_id == current_user.id,
            Resume.file_hash == file_hash,
            Resume.is_deleted == False
        )
    )
    duplicate_resume = dup_result.scalar_one_or_none()
    if duplicate_resume:
        logger.info("Duplicate resume uploaded, returning existing resume", resume_id=str(duplicate_resume.id), user_id=str(current_user.id))
        return {
            "id": str(duplicate_resume.id),
            "title": duplicate_resume.title,
            "file_name": duplicate_resume.file_name,
            "file_type": duplicate_resume.file_type,
            "file_size_bytes": duplicate_resume.file_size,
            "is_primary": duplicate_resume.is_primary,
            "is_parsed": duplicate_resume.is_parsed,
            "version": duplicate_resume.version,
            "is_deleted": duplicate_resume.is_deleted,
            "created_at": duplicate_resume.created_at.isoformat(),
            "message": "Duplicate file detected. Returning existing resume ID.",
        }

    # Fetch max version for this user's resumes (including soft deleted) to determine next version
    version_result = await db.execute(
        select(Resume.version)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.version.desc())
        .limit(1)
    )
    max_version = version_result.scalar() or 0
    new_version = max_version + 1

    # Generate unique resume ID
    resume_id = uuid.uuid4()
    storage_path = f"resumes/{current_user.id}/{resume_id}.{file_ext}"

    # Upload to Supabase Storage
    try:
        storage_service = get_storage_service()
        await storage_service.upload_file(
            bucket="resumes",
            path=storage_path,
            content=content,
            content_type=file.content_type or "application/octet-stream"
        )
    except Exception as e:
        logger.error("Failed to upload file to Supabase Storage", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to Supabase cloud storage: {str(e)}"
        )

    # Force this new version to automatically become primary (unset others)
    await db.execute(
        update(Resume)
        .where(Resume.user_id == current_user.id)
        .values(is_primary=False)
    )

    # Create Resume record
    resume = Resume(
        id=resume_id,
        user_id=current_user.id,
        title=title.strip(),
        file_name=file.filename or f"{resume_id}.{file_ext}",
        storage_path=storage_path,
        file_size=len(content),
        file_type=file_ext,
        is_primary=True,
        uploaded_at=datetime.now(timezone.utc),
        file_hash=file_hash,
        version=new_version,
        is_deleted=False,
    )
    db.add(resume)
    await db.flush()

    # Queue background processing
    background_tasks.add_task(
        _process_resume_background,
        str(resume.id),
        storage_path,
        file_ext,
        str(current_user.id),
    )

    await db.commit()
    await db.refresh(resume)

    resume_uploads_total.labels(status="success").inc()
    logger.info("Resume uploaded successfully to Supabase", resume_id=str(resume.id), user_id=str(current_user.id), version=resume.version)

    return {
        "id": str(resume.id),
        "title": resume.title,
        "file_name": resume.file_name,
        "file_type": resume.file_type,
        "file_size_bytes": resume.file_size,
        "is_primary": resume.is_primary,
        "is_parsed": resume.is_parsed,
        "version": resume.version,
        "is_deleted": resume.is_deleted,
        "created_at": resume.created_at.isoformat(),
        "message": "Resume uploaded successfully to cloud. Parsing in progress...",
    }


@router.get("/")
async def list_resumes(
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all resumes for the authenticated user."""
    query = select(Resume).where(Resume.user_id == current_user.id)
    if not include_deleted:
        query = query.where(Resume.is_deleted == False)
    
    query = query.order_by(Resume.created_at.desc())
    result = await db.execute(query)
    resumes = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "file_name": r.file_name,
                "file_type": r.file_type,
                "file_size_bytes": r.file_size,
                "is_primary": r.is_primary,
                "is_parsed": r.is_parsed,
                "version": r.version,
                "is_deleted": r.is_deleted,
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
    if current_user.role == 'admin':
        result = await db.execute(
            select(Resume).where(Resume.id == uuid.UUID(resume_id))
        )
    else:
        result = await db.execute(
            select(Resume).where(
                Resume.id == uuid.UUID(resume_id),
                Resume.user_id == current_user.id,
            )
        )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if resume.is_deleted and current_user.role != 'admin':
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
        "version": resume.version,
        "is_deleted": resume.is_deleted,
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
    permanent: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a resume (soft delete by default, admin can hard delete)."""
    if current_user.role == 'admin':
        result = await db.execute(
            select(Resume).where(Resume.id == uuid.UUID(resume_id))
        )
    else:
        result = await db.execute(
            select(Resume).where(
                Resume.id == uuid.UUID(resume_id),
                Resume.user_id == current_user.id,
            )
        )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if permanent:
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can permanently delete resumes."
            )

        # Hard delete: delete from Supabase Storage first
        try:
            storage_service = get_storage_service()
            await storage_service.delete_file("resumes", resume.storage_path)
        except Exception as e:
            logger.warning("Failed to delete resume file from Supabase Storage during permanent purge", error=str(e))

        await db.delete(resume)
        await db.commit()
        logger.info("Resume permanently deleted", resume_id=resume_id, user_id=str(current_user.id))
    else:
        # Soft delete: update flags
        resume.is_deleted = True
        resume.deleted_at = datetime.now(timezone.utc)

        # If deleted resume was primary, unset it and find the latest active resume to set as primary
        if resume.is_primary:
            resume.is_primary = False
            active_res_result = await db.execute(
                select(Resume)
                .where(
                    Resume.user_id == resume.user_id,
                    Resume.is_deleted == False
                )
                .order_by(Resume.version.desc())
                .limit(1)
            )
            latest_active = active_res_result.scalar_one_or_none()
            if latest_active:
                latest_active.is_primary = True

        await db.commit()
        logger.info("Resume soft deleted", resume_id=resume_id, user_id=str(current_user.id))


@router.post("/{resume_id}/restore")
async def restore_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore a soft-deleted resume."""
    if current_user.role == 'admin':
        result = await db.execute(
            select(Resume).where(Resume.id == uuid.UUID(resume_id))
        )
    else:
        result = await db.execute(
            select(Resume).where(
                Resume.id == uuid.UUID(resume_id),
                Resume.user_id == current_user.id,
            )
        )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.is_deleted:
        return {"message": "Resume is already active", "id": str(resume.id)}

    resume.is_deleted = False
    resume.deleted_at = None

    # If there are no other active resumes that are primary, set this as primary
    primary_check = await db.execute(
        select(Resume).where(
            Resume.user_id == resume.user_id,
            Resume.is_primary == True,
            Resume.is_deleted == False
        )
    )
    if not primary_check.scalar_one_or_none():
        # Unset any other primary
        await db.execute(
            update(Resume)
            .where(Resume.user_id == resume.user_id)
            .values(is_primary=False)
        )
        resume.is_primary = True

    await db.commit()
    await db.refresh(resume)
    logger.info("Resume restored", resume_id=resume_id, user_id=str(current_user.id))

    return {
        "id": str(resume.id),
        "title": resume.title,
        "is_primary": resume.is_primary,
        "is_deleted": resume.is_deleted,
        "message": "Resume restored successfully",
    }


@router.post("/{resume_id}/primary")
async def set_primary_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a specific resume as primary for the user."""
    if current_user.role == 'admin':
        result = await db.execute(
            select(Resume).where(Resume.id == uuid.UUID(resume_id))
        )
    else:
        result = await db.execute(
            select(Resume).where(
                Resume.id == uuid.UUID(resume_id),
                Resume.user_id == current_user.id,
            )
        )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if resume.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot set a deleted resume as primary")

    # Unset current primary for the owner of this resume
    await db.execute(
        update(Resume)
        .where(Resume.user_id == resume.user_id)
        .values(is_primary=False)
    )

    resume.is_primary = True
    await db.commit()
    await db.refresh(resume)
    logger.info("Primary resume updated", resume_id=resume_id, user_id=str(resume.user_id))

    return {
        "id": str(resume.id),
        "title": resume.title,
        "is_primary": resume.is_primary,
        "message": "Resume set as primary successfully",
    }
