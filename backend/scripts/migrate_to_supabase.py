import os
import sys
import asyncio
import uuid
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
import structlog

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(backend_dir))

# Set environmental variable to load the correct .env
os.environ["ENV_FILE"] = str(backend_dir / ".env")

from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.models.postgres_models import (
    User, Resume, ParsedResume, Embedding, Job, JobDescription,
    Application, CoverLetter, Feedback, Recommendation, AuditLog
)
from app.services.embedding_service import get_embedding_service
from app.services.supabase_storage import get_storage_service

logger = structlog.get_logger(__name__)

# Global migration stats
stats = {
    "users": {"read": 0, "migrated": 0, "errors": 0},
    "resumes": {"read": 0, "migrated": 0, "files_uploaded": 0, "errors": 0},
    "parsed_resumes": {"read": 0, "migrated": 0, "embeddings_created": 0, "errors": 0},
    "jobs": {"read": 0, "migrated": 0, "embeddings_created": 0, "errors": 0},
    "job_descriptions": {"read": 0, "migrated": 0, "errors": 0},
    "applications": {"read": 0, "migrated": 0, "errors": 0},
    "cover_letters": {"read": 0, "migrated": 0, "errors": 0},
    "feedback": {"read": 0, "migrated": 0, "errors": 0},
    "recommendations": {"read": 0, "migrated": 0, "errors": 0},
    "audit_logs": {"read": 0, "migrated": 0, "errors": 0},
}
warnings = []
errors = []

def dict_from_row(row, cursor):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def parse_sqlite_timestamp(val):
    if not val:
        return datetime.now(timezone.utc)
    try:
        # Standard iso format or sqlite format
        if "T" in val:
            # handle fractional seconds or timezone suffixes
            cleaned = val.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        else:
            return datetime.strptime(val.split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return datetime.now(timezone.utc)

async def migrate_data():
    sqlite_db_path = backend_dir / "resumesh.db"
    if not sqlite_db_path.exists():
        logger.error("SQLite database not found", path=str(sqlite_db_path))
        print(f"Error: SQLite database not found at {sqlite_db_path}")
        return

    logger.info("Dropping all existing target tables in Supabase for a clean migration...")
    print("Dropping all existing target tables in Supabase for a clean migration...")
    from app.core.database import engine
    from sqlalchemy import text
    async with engine.begin() as conn:
        for table in ["audit_logs", "feedback", "recommendations", "cover_letters", "applications", 
                      "job_descriptions", "jobs", "embeddings", "parsed_resumes", "resumes", "users"]:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))

    logger.info("Initializing target Supabase database and vector extension...")
    print("Initializing target Supabase database and vector extension...")
    await init_db()

    # Connect to SQLite
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    # Setup storage service
    storage_service = get_storage_service()
    await storage_service.initialize_bucket("resumes")

    # Setup embedding service
    embedding_service = get_embedding_service()
    await embedding_service.initialize()

    # 1. MIGRATE USERS
    print("\n--- Migrating Users ---")
    cursor.execute("SELECT * FROM users")
    user_rows = cursor.fetchall()
    stats["users"]["read"] = len(user_rows)

    async with AsyncSessionLocal() as session:
        for row in user_rows:
            data = dict_from_row(row, cursor)
            try:
                # Upsert user into postgres
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                updated_at = parse_sqlite_timestamp(data.get("updated_at"))
                last_login_at = parse_sqlite_timestamp(data.get("last_login_at")) if data.get("last_login_at") else None

                pg_user = User(
                    id=uuid.UUID(data["id"]),
                    email=data["email"],
                    hashed_password=data.get("hashed_password"),
                    full_name=data["full_name"],
                    role=data.get("role", "user"),
                    is_active=bool(data.get("is_active", 1)),
                    is_verified=bool(data.get("is_verified", 0)),
                    avatar_url=data.get("avatar_url"),
                    headline=data.get("headline"),
                    bio=data.get("bio"),
                    location=data.get("location"),
                    linkedin_url=data.get("linkedin_url"),
                    github_url=data.get("github_url"),
                    portfolio_url=data.get("portfolio_url"),
                    created_at=created_at,
                    updated_at=updated_at,
                    last_login_at=last_login_at
                )
                await session.merge(pg_user)
                stats["users"]["migrated"] += 1
            except Exception as e:
                stats["users"]["errors"] += 1
                err_msg = f"Failed to migrate user {data.get('email')}: {str(e)}"
                errors.append(err_msg)
                logger.error("User migration error", email=data.get("email"), error=str(e))
        await session.commit()
    print(f"Migrated {stats['users']['migrated']}/{stats['users']['read']} users.")

    # 2. MIGRATE RESUMES & UPLOAD FILES
    print("\n--- Migrating Resumes ---")
    cursor.execute("SELECT * FROM resumes")
    resume_rows = cursor.fetchall()
    stats["resumes"]["read"] = len(resume_rows)

    async with AsyncSessionLocal() as session:
        for row in resume_rows:
            data = dict_from_row(row, cursor)
            resume_uuid = uuid.UUID(data["id"])
            user_uuid = uuid.UUID(data["user_id"])
            file_name = data["file_name"]
            file_type = data.get("file_type") or file_name.split(".")[-1].lower()
            storage_path = f"resumes/{user_uuid}/{resume_uuid}.{file_type}"

            # Try to upload file to Supabase Storage
            # Get path from SQLite file_path column
            file_path_val = data.get("file_path")
            local_file_path = None
            if file_path_val:
                local_file_path = backend_dir / file_path_val.replace("\\", "/")
            
            if not local_file_path or not local_file_path.exists():
                # Try fallback of searching in uploads recursively
                found = False
                for p in (backend_dir / "uploads").glob(f"**/{resume_uuid}.{file_type}"):
                    local_file_path = p
                    found = True
                    break
                if not found:
                    # Also try search by file_name
                    for p in (backend_dir / "uploads").glob(f"**/{file_name}"):
                        local_file_path = p
                        found = True
                        break
                if not found:
                    warn_msg = f"Local file not found for resume {resume_uuid} ({file_name}). Skipped upload."
                    warnings.append(warn_msg)
                    logger.warning("Local resume file not found", resume_id=str(resume_uuid), file_name=file_name)

            uploaded_to_storage = False
            file_size_bytes = data.get("file_size", 0)
            if local_file_path.exists():
                try:
                    file_size_bytes = local_file_path.stat().st_size
                    with open(local_file_path, "rb") as f:
                        file_content = f.read()

                    await storage_service.upload_file(
                        bucket="resumes",
                        path=storage_path,
                        content=file_content,
                        content_type="application/pdf" if file_type == "pdf" else "application/octet-stream"
                    )
                    stats["resumes"]["files_uploaded"] += 1
                    uploaded_to_storage = True
                except Exception as e:
                    warn_msg = f"Failed to upload file {local_file_path} to Supabase Storage: {str(e)}"
                    warnings.append(warn_msg)
                    logger.error("Storage upload failed", path=str(local_file_path), error=str(e))

            try:
                uploaded_at = parse_sqlite_timestamp(data.get("uploaded_at") or data.get("created_at"))
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                updated_at = parse_sqlite_timestamp(data.get("updated_at"))

                pg_resume = Resume(
                    id=resume_uuid,
                    user_id=user_uuid,
                    file_name=file_name,
                    storage_path=storage_path,
                    file_size=file_size_bytes,
                    file_type=file_type,
                    uploaded_at=uploaded_at,
                    title=data.get("title", file_name),
                    is_primary=bool(data.get("is_primary", 0)),
                    is_parsed=bool(data.get("is_parsed", 0)),
                    chroma_doc_id=data.get("chroma_doc_id"),
                    created_at=created_at,
                    updated_at=updated_at
                )
                await session.merge(pg_resume)
                stats["resumes"]["migrated"] += 1
            except Exception as e:
                stats["resumes"]["errors"] += 1
                err_msg = f"Failed to migrate resume record {resume_uuid}: {str(e)}"
                errors.append(err_msg)
                logger.error("Resume migration error", id=str(resume_uuid), error=str(e))
        await session.commit()
    print(f"Migrated {stats['resumes']['migrated']}/{stats['resumes']['read']} resumes. Files uploaded: {stats['resumes']['files_uploaded']}.")

    # 3. MIGRATE PARSED RESUMES & EMBEDDINGS
    print("\n--- Migrating Parsed Resumes & Embeddings ---")
    cursor.execute("SELECT * FROM parsed_resumes")
    parsed_rows = cursor.fetchall()
    stats["parsed_resumes"]["read"] = len(parsed_rows)

    async with AsyncSessionLocal() as session:
        for row in parsed_rows:
            data = dict_from_row(row, cursor)
            resume_uuid = uuid.UUID(data["resume_id"])

            skills_val = data.get("skills")
            education_val = data.get("education")
            experience_val = data.get("experience")
            projects_val = data.get("projects")
            certifications_val = data.get("certifications")
            languages_val = data.get("languages")
            parsed_json_val = data.get("parsed_json")

            # Parse JSON values if stored as string
            def try_parse_json(val):
                if not val:
                    return None
                if isinstance(val, (dict, list)):
                    return val
                try:
                    return json.loads(val)
                except Exception:
                    return val

            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                updated_at = parse_sqlite_timestamp(data.get("updated_at"))

                # Recreate parsed JSON structure if missing
                parsed_json = try_parse_json(parsed_json_val)
                if not parsed_json:
                    parsed_json = {
                        "name": data.get("name") or data.get("full_name") or "",
                        "email": data.get("email") or "",
                        "phone": data.get("phone") or "",
                        "skills": try_parse_json(skills_val) or [],
                        "education": try_parse_json(education_val) or [],
                        "experience": try_parse_json(experience_val) or [],
                        "projects": try_parse_json(projects_val) or []
                    }

                pg_parsed = ParsedResume(
                    id=uuid.UUID(data["id"]) if data.get("id") else uuid.uuid4(),
                    resume_id=resume_uuid,
                    name=data.get("name") or data.get("full_name"),
                    email=data.get("email"),
                    phone=data.get("phone"),
                    skills=try_parse_json(skills_val),
                    education=try_parse_json(education_val),
                    experience=try_parse_json(experience_val),
                    projects=try_parse_json(projects_val),
                    parsed_json=parsed_json,
                    raw_text=data.get("raw_text"),
                    full_name=data.get("full_name") or data.get("name"),
                    location=data.get("location"),
                    linkedin_url=data.get("linkedin_url"),
                    github_url=data.get("github_url"),
                    certifications=try_parse_json(certifications_val),
                    languages=try_parse_json(languages_val),
                    total_years_experience=float(data.get("total_years_experience")) if data.get("total_years_experience") else None,
                    seniority_level=data.get("seniority_level"),
                    created_at=created_at,
                    updated_at=updated_at
                )
                await session.merge(pg_parsed)
                stats["parsed_resumes"]["migrated"] += 1

                # Generate Embedding using sentence-transformers (pgvector)
                raw_text = data.get("raw_text", "")
                if raw_text:
                    try:
                        emb = await embedding_service.encode(raw_text)
                        # Check if embedding already exists
                        from sqlalchemy import select
                        emb_result = await session.execute(
                            select(Embedding).where(Embedding.resume_id == resume_uuid)
                        )
                        pg_emb = emb_result.scalar_one_or_none()
                        if pg_emb:
                            pg_emb.embedding = emb
                        else:
                            pg_emb = Embedding(
                                id=uuid.uuid4(),
                                resume_id=resume_uuid,
                                embedding=emb,
                                created_at=datetime.now(timezone.utc)
                            )
                            session.add(pg_emb)
                        stats["parsed_resumes"]["embeddings_created"] += 1
                    except Exception as emb_e:
                        warn_msg = f"Failed to generate embedding for parsed resume {resume_uuid}: {str(emb_e)}"
                        warnings.append(warn_msg)
                        logger.error("Embedding generation failed", resume_id=str(resume_uuid), error=str(emb_e))

            except Exception as e:
                stats["parsed_resumes"]["errors"] += 1
                err_msg = f"Failed to migrate parsed resume for {resume_uuid}: {str(e)}"
                errors.append(err_msg)
                logger.error("Parsed resume migration error", resume_id=str(resume_uuid), error=str(e))
        await session.commit()
    print(f"Migrated {stats['parsed_resumes']['migrated']}/{stats['parsed_resumes']['read']} parsed resumes. Embeddings created: {stats['parsed_resumes']['embeddings_created']}.")

    # 4. MIGRATE JOBS
    print("\n--- Migrating Jobs ---")
    cursor.execute("SELECT * FROM jobs")
    job_rows = cursor.fetchall()
    stats["jobs"]["read"] = len(job_rows)

    async with AsyncSessionLocal() as session:
        for row in job_rows:
            data = dict_from_row(row, cursor)
            job_uuid = uuid.UUID(data["id"])
            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                updated_at = parse_sqlite_timestamp(data.get("updated_at"))

                # Recreate job embedding
                raw_desc = data.get("raw_description", "")
                emb = None
                if raw_desc:
                    try:
                        emb = await embedding_service.encode(raw_desc)
                        stats["jobs"]["embeddings_created"] += 1
                    except Exception as emb_e:
                        warn_msg = f"Failed to generate embedding for job {job_uuid}: {str(emb_e)}"
                        warnings.append(warn_msg)

                pg_job = Job(
                    id=job_uuid,
                    title=data["title"],
                    description=data.get("description") or raw_desc,
                    requirements=data.get("requirements"),
                    embedding=emb,
                    created_at=created_at,
                    company=data.get("company", "Unknown Company"),
                    location=data.get("location"),
                    job_type=data.get("job_type"),
                    experience_level=data.get("experience_level"),
                    salary_range=data.get("salary_range"),
                    portal=data.get("portal", "manual"),
                    portal_job_id=data.get("portal_job_id"),
                    job_url=data.get("job_url"),
                    raw_description=raw_desc,
                    chroma_doc_id=data.get("chroma_doc_id"),
                    updated_at=updated_at
                )
                await session.merge(pg_job)
                stats["jobs"]["migrated"] += 1
            except Exception as e:
                stats["jobs"]["errors"] += 1
                err_msg = f"Failed to migrate job {job_uuid}: {str(e)}"
                errors.append(err_msg)
                logger.error("Job migration error", id=str(job_uuid), error=str(e))
        await session.commit()
    print(f"Migrated {stats['jobs']['migrated']}/{stats['jobs']['read']} jobs. Embeddings created: {stats['jobs']['embeddings_created']}.")

    # 5. MIGRATE JOB DESCRIPTIONS
    print("\n--- Migrating Job Descriptions ---")
    cursor.execute("SELECT * FROM job_descriptions")
    jd_rows = cursor.fetchall()
    stats["job_descriptions"]["read"] = len(jd_rows)

    async with AsyncSessionLocal() as session:
        for row in jd_rows:
            data = dict_from_row(row, cursor)
            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                pg_jd = JobDescription(
                    id=uuid.UUID(data["id"]) if data.get("id") else uuid.uuid4(),
                    job_id=uuid.UUID(data["job_id"]),
                    required_skills=try_parse_json(data.get("required_skills")),
                    preferred_skills=try_parse_json(data.get("preferred_skills")),
                    responsibilities=try_parse_json(data.get("responsibilities")),
                    qualifications=try_parse_json(data.get("qualifications")),
                    education_requirements=try_parse_json(data.get("education_requirements")),
                    certifications=try_parse_json(data.get("certifications")),
                    min_years_experience=float(data.get("min_years_experience")) if data.get("min_years_experience") else None,
                    max_years_experience=float(data.get("max_years_experience")) if data.get("max_years_experience") else None,
                    tech_stack=try_parse_json(data.get("tech_stack")),
                    soft_skills=try_parse_json(data.get("soft_skills")),
                    created_at=created_at
                )
                await session.merge(pg_jd)
                stats["job_descriptions"]["migrated"] += 1
            except Exception as e:
                stats["job_descriptions"]["errors"] += 1
                err_msg = f"Failed to migrate job description for job {data.get('job_id')}: {str(e)}"
                errors.append(err_msg)
                logger.error("JobDescription migration error", job_id=data.get("job_id"), error=str(e))
        await session.commit()
    print(f"Migrated {stats['job_descriptions']['migrated']}/{stats['job_descriptions']['read']} job descriptions.")

    # 6. MIGRATE APPLICATIONS
    print("\n--- Migrating Applications ---")
    cursor.execute("SELECT * FROM applications")
    app_rows = cursor.fetchall()
    stats["applications"]["read"] = len(app_rows)

    async with AsyncSessionLocal() as session:
        for row in app_rows:
            data = dict_from_row(row, cursor)
            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                updated_at = parse_sqlite_timestamp(data.get("updated_at"))
                applied_at = parse_sqlite_timestamp(data.get("applied_at")) if data.get("applied_at") else None
                interview_date = parse_sqlite_timestamp(data.get("interview_date")) if data.get("interview_date") else None

                pg_app = Application(
                    id=uuid.UUID(data["id"]),
                    job_id=uuid.UUID(data["job_id"]),
                    resume_id=uuid.UUID(data["resume_id"]) if data.get("resume_id") else None,
                    match_score=float(data.get("match_score")) if data.get("match_score") is not None else None,
                    created_at=created_at,
                    user_id=uuid.UUID(data["user_id"]),
                    status=data.get("status", "saved"),
                    matched_skills=try_parse_json(data.get("matched_skills")),
                    missing_skills=try_parse_json(data.get("missing_skills")),
                    recommendations=try_parse_json(data.get("recommendations")),
                    notes=data.get("notes"),
                    interview_date=interview_date,
                    offer_amount=data.get("offer_amount"),
                    applied_at=applied_at,
                    updated_at=updated_at
                )
                await session.merge(pg_app)
                stats["applications"]["migrated"] += 1
            except Exception as e:
                stats["applications"]["errors"] += 1
                err_msg = f"Failed to migrate application {data.get('id')}: {str(e)}"
                errors.append(err_msg)
                logger.error("Application migration error", id=data.get("id"), error=str(e))
        await session.commit()
    print(f"Migrated {stats['applications']['migrated']}/{stats['applications']['read']} applications.")

    # 7. MIGRATE COVER LETTERS
    print("\n--- Migrating Cover Letters ---")
    cursor.execute("SELECT * FROM cover_letters")
    cl_rows = cursor.fetchall()
    stats["cover_letters"]["read"] = len(cl_rows)

    async with AsyncSessionLocal() as session:
        for row in cl_rows:
            data = dict_from_row(row, cursor)
            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))
                updated_at = parse_sqlite_timestamp(data.get("updated_at"))

                pg_cl = CoverLetter(
                    id=uuid.UUID(data["id"]),
                    user_id=uuid.UUID(data["user_id"]),
                    application_id=uuid.UUID(data["application_id"]) if data.get("application_id") else None,
                    title=data.get("title", "Cover Letter"),
                    content=data["content"],
                    template_used=data.get("template_used"),
                    tone=data.get("tone", "Professional"),
                    word_count=int(data.get("word_count", 0)),
                    is_ai_generated=bool(data.get("is_ai_generated", 1)),
                    llm_model_used=data.get("llm_model_used"),
                    created_at=created_at,
                    updated_at=updated_at
                )
                await session.merge(pg_cl)
                stats["cover_letters"]["migrated"] += 1
            except Exception as e:
                stats["cover_letters"]["errors"] += 1
                err_msg = f"Failed to migrate cover letter {data.get('id')}: {str(e)}"
                errors.append(err_msg)
                logger.error("CoverLetter migration error", id=data.get("id"), error=str(e))
        await session.commit()
    print(f"Migrated {stats['cover_letters']['migrated']}/{stats['cover_letters']['read']} cover letters.")

    # 8. MIGRATE FEEDBACK
    print("\n--- Migrating Feedback ---")
    cursor.execute("SELECT * FROM feedback")
    fb_rows = cursor.fetchall()
    stats["feedback"]["read"] = len(fb_rows)

    async with AsyncSessionLocal() as session:
        for row in fb_rows:
            data = dict_from_row(row, cursor)
            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))

                pg_fb = Feedback(
                    id=uuid.UUID(data["id"]),
                    user_id=uuid.UUID(data["user_id"]),
                    application_id=uuid.UUID(data["application_id"]) if data.get("application_id") else None,
                    feedback_type=data["feedback_type"],
                    rating=int(data["rating"]) if data.get("rating") is not None else None,
                    comment=data.get("comment"),
                    metadata=try_parse_json(data.get("metadata")),
                    created_at=created_at
                )
                await session.merge(pg_fb)
                stats["feedback"]["migrated"] += 1
            except Exception as e:
                stats["feedback"]["errors"] += 1
                err_msg = f"Failed to migrate feedback {data.get('id')}: {str(e)}"
                errors.append(err_msg)
                logger.error("Feedback migration error", id=data.get("id"), error=str(e))
        await session.commit()
    print(f"Migrated {stats['feedback']['migrated']}/{stats['feedback']['read']} feedback items.")

    # 9. MIGRATE RECOMMENDATIONS (IF EXISTS)
    try:
        cursor.execute("SELECT * FROM recommendations")
        rec_rows = cursor.fetchall()
        stats["recommendations"]["read"] = len(rec_rows)
        print("\n--- Migrating Recommendations ---")

        async with AsyncSessionLocal() as session:
            for row in rec_rows:
                data = dict_from_row(row, cursor)
                try:
                    created_at = parse_sqlite_timestamp(data.get("created_at"))
                    pg_rec = Recommendation(
                        id=uuid.UUID(data["id"]),
                        user_id=uuid.UUID(data["user_id"]),
                        application_id=uuid.UUID(data["application_id"]) if data.get("application_id") else None,
                        category=data["category"],
                        title=data["title"],
                        description=data["description"],
                        priority=int(data.get("priority", 1)),
                        resource_url=data.get("resource_url"),
                        is_dismissed=bool(data.get("is_dismissed", 0)),
                        is_completed=bool(data.get("is_completed", 0)),
                        created_at=created_at
                    )
                    await session.merge(pg_rec)
                    stats["recommendations"]["migrated"] += 1
                except Exception as e:
                    stats["recommendations"]["errors"] += 1
                    err_msg = f"Failed to migrate recommendation {data.get('id')}: {str(e)}"
                    errors.append(err_msg)
            await session.commit()
        print(f"Migrated {stats['recommendations']['migrated']}/{stats['recommendations']['read']} recommendations.")
    except sqlite3.OperationalError:
        print("\nSkipped Recommendations: table does not exist in SQLite DB.")

    # 10. MIGRATE AUDIT LOGS
    print("\n--- Migrating Audit Logs ---")
    cursor.execute("SELECT * FROM audit_logs")
    audit_rows = cursor.fetchall()
    stats["audit_logs"]["read"] = len(audit_rows)

    async with AsyncSessionLocal() as session:
        for row in audit_rows:
            data = dict_from_row(row, cursor)
            try:
                created_at = parse_sqlite_timestamp(data.get("created_at"))

                pg_audit = AuditLog(
                    id=uuid.UUID(data["id"]),
                    user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
                    action=data["action"],
                    resource_type=data.get("resource_type"),
                    resource_id=data.get("resource_id"),
                    ip_address=data.get("ip_address"),
                    user_agent=data.get("user_agent"),
                    metadata=try_parse_json(data.get("metadata")),
                    success=bool(data.get("success", 1)),
                    created_at=created_at
                )
                await session.merge(pg_audit)
                stats["audit_logs"]["migrated"] += 1
            except Exception as e:
                stats["audit_logs"]["errors"] += 1
                err_msg = f"Failed to migrate audit log {data.get('id')}: {str(e)}"
                errors.append(err_msg)
                logger.error("AuditLog migration error", id=data.get("id"), error=str(e))
        await session.commit()
    print(f"Migrated {stats['audit_logs']['migrated']}/{stats['audit_logs']['read']} audit logs.")

    conn.close()
    write_migration_report()

def write_migration_report():
    report_path = backend_dir / "migration_report.md"
    print(f"\nWriting migration report to {report_path}...")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ResuMesh Production Migration Report\n\n")
        f.write(f"Migration completed at: **{datetime.now(timezone.utc).isoformat()}**\n\n")
        
        f.write("## Migration Statistics\n\n")
        f.write("| Table / Category | Records in SQLite | Migrated to Supabase | Errors | Details |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for table, s in stats.items():
            details = ""
            if table == "resumes":
                details = f"Files Uploaded: {s['files_uploaded']}"
            elif table == "parsed_resumes":
                details = f"Embeddings Created: {s['embeddings_created']}"
            elif table == "jobs":
                details = f"Embeddings Created: {s['embeddings_created']}"
            f.write(f"| {table} | {s['read']} | {s['migrated']} | {s['errors']} | {details} |\n")
            
        f.write("\n## Warnings\n\n")
        if warnings:
            for w in warnings:
                f.write(f"- {w}\n")
        else:
            f.write("No warnings generated.\n")
            
        f.write("\n## Errors\n\n")
        if errors:
            for err in errors:
                f.write(f"- {err}\n")
        else:
            f.write("No errors generated.\n")

if __name__ == "__main__":
    asyncio.run(migrate_data())
