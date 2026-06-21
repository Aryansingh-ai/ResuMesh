"""
ML Data Ingestion Script
Exports feedback + resume + job data from the database for training.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def export_training_data(output_path: str = "data/raw/feedback.json") -> None:
    """
    Connect to the database and export feedback data joined with
    resume and job information for ML training.
    """
    import os
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select, text

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://resumesh_user:resumesh_password@localhost:5432/resumesh",
    )

    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        # Join feedback with applications, resumes, parsed_resumes, and jobs
        result = await session.execute(text("""
            SELECT
                f.id AS feedback_id,
                f.feedback_type,
                f.rating,
                f.comment,
                f.created_at AS feedback_date,
                a.match_score,
                a.matched_skills,
                a.missing_skills,
                pr.skills AS resume_skills_json,
                pr.total_years_experience AS resume_years_exp,
                pr.seniority_level AS resume_seniority,
                jd.required_skills,
                jd.preferred_skills,
                jd.tech_stack AS job_tech_stack,
                jd.min_years_experience AS required_years_exp,
                jd.education_requirements
            FROM feedback f
            JOIN applications a ON f.application_id = a.id
            JOIN parsed_resumes pr ON a.resume_id = pr.resume_id
            JOIN job_descriptions jd ON a.job_id = jd.job_id
            WHERE f.application_id IS NOT NULL
            AND pr.skills IS NOT NULL
            ORDER BY f.created_at DESC
            LIMIT 10000
        """))

        rows = result.fetchall()
        logger.info(f"Exported {len(rows)} feedback records")

        records = []
        for row in rows:
            # Flatten skills from JSONB
            skills_json = row.resume_skills_json or {}
            all_skills = []
            if isinstance(skills_json, dict):
                for v in skills_json.values():
                    if isinstance(v, list):
                        all_skills.extend(v)

            records.append({
                "feedback_id": str(row.feedback_id),
                "feedback_type": row.feedback_type,
                "rating": row.rating,
                "match_score": float(row.match_score or 0),
                "matched_skills": row.matched_skills or [],
                "missing_skills": row.missing_skills or [],
                "resume_skills": all_skills,
                "resume_years_exp": float(row.resume_years_exp or 0),
                "resume_seniority": row.resume_seniority or "mid",
                "required_skills": row.required_skills or [],
                "preferred_skills": row.preferred_skills or [],
                "required_years_exp": float(row.required_years_exp or 0),
                "job_tech_stack": row.job_tech_stack or [],
            })

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(records, f, indent=2, default=str)

    logger.info(f"Saved {len(records)} records to {output_path}")
    await engine.dispose()


async def generate_synthetic_data(output_path: str = "data/raw/feedback.json", n: int = 500) -> None:
    """
    Generate synthetic training data for cold-start when real feedback is insufficient.
    Creates realistic resume-job matching scenarios with binary labels.
    """
    import random

    random.seed(42)

    TECH_SKILLS = [
        "Python", "JavaScript", "TypeScript", "React", "FastAPI", "Django",
        "Node.js", "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS",
        "GCP", "Azure", "TensorFlow", "PyTorch", "scikit-learn", "pandas",
        "NumPy", "Git", "CI/CD", "REST API", "GraphQL", "SQL", "MongoDB",
        "Kafka", "Spark", "Linux", "Bash", "Java", "Go", "Rust", "C++",
    ]

    records = []
    for i in range(n):
        # Sample required skills
        n_required = random.randint(4, 10)
        required = random.sample(TECH_SKILLS, n_required)

        # Good match: resume has most required skills
        if random.random() < 0.5:
            overlap_ratio = random.uniform(0.6, 1.0)
            resume_skills = list(set(
                random.sample(required, int(len(required) * overlap_ratio)) +
                random.sample(TECH_SKILLS, random.randint(2, 6))
            ))
            years_ratio = random.uniform(0.8, 2.0)
            feedback_type = "good_match"
        else:
            # Bad match: resume lacks most required skills
            overlap_ratio = random.uniform(0.0, 0.4)
            resume_skills = list(set(
                random.sample(required, int(len(required) * overlap_ratio)) +
                random.sample(TECH_SKILLS, random.randint(0, 3))
            ))
            years_ratio = random.uniform(0.0, 0.6)
            feedback_type = "bad_match"

        required_years = random.uniform(1, 8)
        records.append({
            "feedback_id": f"synthetic_{i:04d}",
            "feedback_type": feedback_type,
            "rating": random.randint(4, 5) if feedback_type == "good_match" else random.randint(1, 2),
            "match_score": overlap_ratio * 100,
            "matched_skills": [s for s in resume_skills if s in required],
            "missing_skills": [s for s in required if s not in resume_skills],
            "resume_skills": resume_skills,
            "resume_years_exp": required_years * years_ratio,
            "resume_seniority": random.choice(["entry", "junior", "mid", "senior"]),
            "required_skills": required,
            "preferred_skills": random.sample(TECH_SKILLS, random.randint(2, 5)),
            "required_years_exp": required_years,
            "job_tech_stack": random.sample(TECH_SKILLS, random.randint(3, 7)),
        })

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(records, f, indent=2)

    logger.info(f"Generated {len(records)} synthetic records → {output_path}")


if __name__ == "__main__":
    import sys
    import os

    output = sys.argv[1] if len(sys.argv) > 1 else "data/raw/feedback.json"
    mode = sys.argv[2] if len(sys.argv) > 2 else "auto"

    if mode == "synthetic" or not os.getenv("DATABASE_URL"):
        logger.info("Generating synthetic training data...")
        asyncio.run(generate_synthetic_data(output, n=1000))
    else:
        logger.info("Exporting real feedback data from DB...")
        asyncio.run(export_training_data(output))
