import uuid
import structlog
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.postgres_models import Embedding, ParsedResume, Job, Resume, JobDescription
from app.services.embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)

class MatchingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def find_top_candidates(self, job_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find top matching resumes for a job using a two-stage matching architecture:
        Stage 1: Retrieve top 100 candidates based on fast pgvector cosine similarity.
        Stage 2: Re-rank the top candidates in Python using the hybrid score algorithm
                 (60% semantic similarity, 20% skills, 10% experience, 10% education).
        """
        # Load Job
        res = await self.db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = res.scalar_one_or_none()
        if not job or job.embedding is None:
            logger.warning("Job or job embedding not found", job_id=job_id)
            return []

        query_embedding = job.embedding

        # Load Job Description for skills, education and experience
        desc_res = await self.db.execute(
            select(JobDescription).where(JobDescription.job_id == job.id)
        )
        job_desc = desc_res.scalar_one_or_none()

        required_skills = job_desc.required_skills or [] if job_desc else []
        preferred_skills = job_desc.preferred_skills or [] if job_desc else []
        education_requirements = job_desc.education_requirements or [] if job_desc else []
        min_years_experience = job_desc.min_years_experience if job_desc else None
        max_years_experience = job_desc.max_years_experience if job_desc else None

        # Stage 1: Fast pgvector query to retrieve top 100 non-deleted resumes
        is_sqlite = False
        try:
            if self.db.bind and "sqlite" in str(self.db.bind.url):
                is_sqlite = True
        except Exception:
            pass

        if is_sqlite:
            # SQLite fallback for local test suites (computes cosine similarity in Python)
            stmt = (
                select(
                    Embedding.resume_id,
                    ParsedResume.full_name,
                    Embedding.embedding,
                    ParsedResume.skills,
                    ParsedResume.education,
                    ParsedResume.experience,
                    ParsedResume.total_years_experience,
                    Resume.title
                )
                .join(Resume, Resume.id == Embedding.resume_id)
                .join(ParsedResume, ParsedResume.resume_id == Embedding.resume_id)
                .where(Resume.is_deleted == False)
                .limit(100)
            )
            result = await self.db.execute(stmt)
            
            import numpy as np
            q_vec = np.array(query_embedding)
            q_norm = np.linalg.norm(q_vec)
            
            rows = []
            for r in result.all():
                resume_id, full_name, emb_val, skills, education, experience, total_years_exp, resume_title = r
                emb_vec = np.array(emb_val)
                emb_norm = np.linalg.norm(emb_vec)
                if q_norm > 0 and emb_norm > 0:
                    sim = float(np.dot(q_vec, emb_vec) / (q_norm * emb_norm))
                else:
                    sim = 0.0
                rows.append((resume_id, full_name, sim, skills, education, experience, total_years_exp, resume_title))
            rows.sort(key=lambda x: x[2], reverse=True)
        else:
            # Production pgvector query on Supabase PostgreSQL (uses HNSW index)
            stmt = (
                select(
                    Embedding.resume_id,
                    ParsedResume.full_name,
                    (1 - Embedding.embedding.cosine_distance(query_embedding)).label("embedding_score"),
                    ParsedResume.skills,
                    ParsedResume.education,
                    ParsedResume.experience,
                    ParsedResume.total_years_experience,
                    Resume.title
                )
                .join(Resume, Resume.id == Embedding.resume_id)
                .join(ParsedResume, ParsedResume.resume_id == Embedding.resume_id)
                .where(Resume.is_deleted == False)
                .order_by(Embedding.embedding.cosine_distance(query_embedding))
                .limit(100)
            )
            result = await self.db.execute(stmt)
            rows = result.all()
        
        candidates = []
        
        # Stage 2: Hybrid re-ranking
        for row in rows:
            resume_id, full_name, embedding_score_raw, skills, education, experience, total_years_exp, resume_title = row
            
            # 1. Scaling embedding score to 0 - 100
            embedding_score = round(min(max(float(embedding_score_raw or 0.0) * 100.0, 0.0), 100.0), 1)

            # 2. Skill matching score
            resume_skills: List[str] = []
            if isinstance(skills, dict):
                for skills_list in skills.values():
                    if isinstance(skills_list, list):
                        resume_skills.extend([s.lower() for s in skills_list if s])
            elif isinstance(skills, list):
                resume_skills.extend([s.lower() for s in skills if s])
            elif isinstance(skills, str):
                resume_skills.extend([s.strip().lower() for s in skills.split(",") if s])
            resume_skills_set = set(resume_skills)

            req_skills_lower = [s.lower() for s in required_skills if s]
            pref_skills_lower = [s.lower() for s in preferred_skills if s]

            matched_req = [s for s in req_skills_lower if s in resume_skills_set]
            matched_pref = [s for s in pref_skills_lower if s in resume_skills_set]

            if req_skills_lower:
                req_coverage = len(matched_req) / len(req_skills_lower)
                pref_coverage = len(matched_pref) / max(len(pref_skills_lower), 1)
                skill_score = (req_coverage * 0.8 + pref_coverage * 0.2) * 100.0
            elif not req_skills_lower and not pref_skills_lower:
                skill_score = 75.0
            else:
                skill_score = 50.0

            skill_score = round(min(max(skill_score, 0.0), 100.0), 1)

            # 3. Experience matching score
            resume_years = float(total_years_exp or 0.0)
            if min_years_experience is None:
                exp_score = 75.0
            else:
                min_years = float(min_years_experience)
                if resume_years >= min_years:
                    if max_years_experience and resume_years > float(max_years_experience) * 1.5:
                        exp_score = 70.0
                    else:
                        exp_score = 100.0
                else:
                    deficit = min_years - resume_years
                    exp_score = max(0.0, 100.0 - (deficit * 15))
            
            exp_score = round(min(max(exp_score, 0.0), 100.0), 1)

            # 4. Education matching score
            if not education_requirements:
                edu_score = 75.0
            else:
                resume_edu_list = education or []
                resume_edu_text = " ".join([str(e) for e in resume_edu_list]).lower()

                degree_hierarchy = {"phd": 4, "master": 3, "bachelor": 2, "associate": 1}
                req_level = 0
                for deg in education_requirements:
                    for key, level in degree_hierarchy.items():
                        if key in str(deg).lower():
                            req_level = max(req_level, level)

                resume_level = 0
                for key, level in degree_hierarchy.items():
                    if key in resume_edu_text:
                        resume_level = max(resume_level, level)

                if resume_level >= req_level:
                    edu_score = 100.0
                elif resume_level == req_level - 1:
                    edu_score = 70.0
                else:
                    edu_score = 40.0

            edu_score = round(min(max(edu_score, 0.0), 100.0), 1)

            # 5. Hybrid score calculation (60/20/10/10)
            final_score = round(
                0.60 * embedding_score +
                0.20 * skill_score +
                0.10 * exp_score +
                0.10 * edu_score,
                1
            )

            candidates.append({
                "resume_id": str(resume_id),
                "candidate_name": full_name or "Unknown Candidate",
                "resume_title": resume_title or "Untitled Resume",
                "score": final_score,
                "score_breakdown": {
                    "final_score": final_score,
                    "embedding_score": embedding_score,
                    "skill_score": skill_score,
                    "experience_score": exp_score,
                    "education_score": edu_score
                },
                "details": {
                    "final_score": final_score,
                    "embedding_score": embedding_score,
                    "skill_score": skill_score,
                    "experience_score": exp_score,
                    "education_score": edu_score,
                    "skills_match": skill_score,
                    "semantic_match": embedding_score,
                    "experience_match": exp_score,
                    "education_match": edu_score,
                    "matched_skills": [s for s in required_skills if s.lower() in resume_skills_set],
                    "missing_skills": [s for s in required_skills if s.lower() not in resume_skills_set]
                }
            })
            
        candidates.sort(key=lambda x: x["score"], reverse=True)
        logger.info("Hybrid candidates match complete", job_id=job_id, count=len(candidates))
        return candidates[:limit]

    async def match_by_text(self, text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Match candidates by a raw job description query text."""
        query_embedding = await self.embedding_service.encode(text)
        
        stmt = (
            select(
                Embedding.resume_id,
                ParsedResume.full_name,
                (1 - Embedding.embedding.cosine_distance(query_embedding)).label("score"),
                Resume.title
            )
            .join(Resume, Resume.id == Embedding.resume_id)
            .join(ParsedResume, ParsedResume.resume_id == Embedding.resume_id)
            .where(Resume.is_deleted == False)
            .order_by(Embedding.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        candidates = []
        for row in result.all():
            candidates.append({
                "resume_id": str(row[0]),
                "candidate_name": row[1] or "Unknown Candidate",
                "resume_title": row[3] or "Untitled Resume",
                "score": round(float(row[2]) * 100, 1),
                "score_breakdown": {
                    "final_score": round(float(row[2]) * 100, 1),
                    "embedding_score": round(float(row[2]) * 100, 1),
                    "skill_score": 0,
                    "experience_score": 0,
                    "education_score": 0
                },
                "details": {
                    "final_score": round(float(row[2]) * 100, 1),
                    "embedding_score": round(float(row[2]) * 100, 1),
                    "skill_score": 0,
                    "experience_score": 0,
                    "education_score": 0,
                    "skills_match": 0,
                    "semantic_match": round(float(row[2]) * 100, 1),
                    "experience_match": 0,
                    "education_match": 0,
                    "matched_skills": [],
                    "missing_skills": []
                }
            })
        return candidates

