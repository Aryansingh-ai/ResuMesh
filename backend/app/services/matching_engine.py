"""
Matching Engine — Three-version resume-to-job matching system.
V1: Weighted Keyword Matching
V2: Embedding Similarity (Sentence Transformers + ChromaDB)
V3: Feedback-Based Ranking
"""

import re
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import structlog

from app.core.config import settings
from app.core.metrics import match_score_histogram

logger = structlog.get_logger(__name__)


@dataclass
class MatchResult:
    """Result of a resume-job matching operation."""
    score: float  # 0–100
    matched_skills: List[str]
    missing_skills: List[str]
    recommendations: List[Dict[str, Any]]
    details: Dict[str, Any]
    model_version: str


class MatchingEngine:
    """
    Multi-version matching engine for resume-to-job comparison.
    Uses best available method based on configuration.
    """

    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service

    async def match(
        self,
        parsed_resume: Dict[str, Any],
        job_description: Dict[str, Any],
        raw_resume_text: str = "",
        raw_job_text: str = "",
        use_embeddings: bool = True,
    ) -> MatchResult:
        """
        Compute match score using all available methods and combine results.

        Args:
            parsed_resume: Structured parsed resume data.
            job_description: Structured parsed job description.
            raw_resume_text: Raw resume text for embedding.
            raw_job_text: Raw job description for embedding.
            use_embeddings: Whether to use embedding similarity.

        Returns:
            MatchResult with score, skills, and recommendations.
        """
        # V1: Keyword matching (always available)
        v1_result = self._keyword_match(parsed_resume, job_description)

        # V2: Embedding similarity (if service available)
        v2_score = None
        if use_embeddings and self.embedding_service and raw_resume_text and raw_job_text:
            try:
                v2_score = await self.embedding_service.compute_similarity(
                    raw_resume_text, raw_job_text
                )
            except Exception as e:
                logger.warning("Embedding similarity failed, using keyword only", error=str(e))

        # Retrieve subscores from helper methods
        exp_score = self._compute_experience_score(parsed_resume, job_description)
        edu_score = self._compute_education_score(parsed_resume, job_description)

        # Flatten resume skills
        resume_skills_dict = parsed_resume.get("skills", {})
        resume_skills: List[str] = []
        if isinstance(resume_skills_dict, dict):
            for skills_list in resume_skills_dict.values():
                if isinstance(skills_list, list):
                    resume_skills.extend([s.lower() for s in skills_list if s])
        elif isinstance(resume_skills_dict, list):
            resume_skills.extend([s.lower() for s in resume_skills_dict if s])
        elif isinstance(resume_skills_dict, str):
            resume_skills.extend([s.strip().lower() for s in resume_skills_dict.split(",") if s])
        resume_skills_set = set(resume_skills)

        required_skills = [s.lower() for s in (job_description.get("required_skills") or [])]
        preferred_skills = [s.lower() for s in (job_description.get("preferred_skills") or [])]

        matched_req = [s for s in required_skills if s in resume_skills_set]
        matched_pref = [s for s in preferred_skills if s in resume_skills_set]

        if required_skills:
            req_coverage = len(matched_req) / len(required_skills)
            pref_coverage = len(matched_pref) / max(len(preferred_skills), 1)
            skill_score = (req_coverage * 0.8 + pref_coverage * 0.2) * 100.0
        elif not required_skills and not preferred_skills:
            skill_score = 75.0
        else:
            skill_score = 50.0

        # Combine scores
        if v2_score is not None:
            embedding_score = round(min(max(float(v2_score) * 100.0, 0.0), 100.0), 1)
            final_score = 0.60 * embedding_score + 0.20 * skill_score + 0.10 * exp_score + 0.10 * edu_score
            model_version = "v2_hybrid"
        else:
            embedding_score = 0.0
            final_score = v1_result["score"]
            model_version = "v1_keyword"

        final_score = round(min(max(final_score, 0.0), 100.0), 1)

        # Record metric
        match_score_histogram.observe(final_score)

        result = MatchResult(
            score=final_score,
            matched_skills=v1_result["matched_skills"],
            missing_skills=v1_result["missing_skills"],
            recommendations=self._generate_recommendations(
                v1_result["missing_skills"],
                parsed_resume,
                job_description,
            ),
            details={
                "final_score": final_score,
                "embedding_score": embedding_score,
                "skill_score": round(skill_score, 1),
                "experience_score": round(exp_score, 1),
                "education_score": round(edu_score, 1),
                "skills_match": round(skill_score, 1),
                "semantic_match": embedding_score,
                "experience_match": round(exp_score, 1),
                "education_match": round(edu_score, 1),
                "keyword_score": v1_result["score"],
                "skill_coverage": v1_result["skill_coverage"],
            },
            model_version=model_version,
        )

        logger.info(
            "Match computed",
            score=final_score,
            matched=len(result.matched_skills),
            missing=len(result.missing_skills),
            version=model_version,
        )
        return result

    def _keyword_match(
        self,
        parsed_resume: Dict[str, Any],
        job_description: Dict[str, Any],
    ) -> Dict[str, Any]:
        """V1: Weighted keyword matching across multiple dimensions."""

        # Flatten resume skills
        resume_skills_dict = parsed_resume.get("skills", {})
        resume_skills: List[str] = []
        for skills_list in resume_skills_dict.values():
            resume_skills.extend([s.lower() for s in (skills_list or [])])
        resume_skills_set = set(resume_skills)

        # Job required skills
        required_skills: List[str] = [
            s.lower() for s in (job_description.get("required_skills") or [])
        ]
        preferred_skills: List[str] = [
            s.lower() for s in (job_description.get("preferred_skills") or [])
        ]
        all_job_skills = list(set(required_skills + preferred_skills))

        # Skill matching
        matched = [s for s in required_skills if s in resume_skills_set]
        matched_preferred = [s for s in preferred_skills if s in resume_skills_set]
        missing = [s for s in required_skills if s not in resume_skills_set]

        # Skill coverage score (50% weight)
        skill_score = 0.0
        if required_skills:
            req_coverage = len(matched) / len(required_skills)
            pref_coverage = len(matched_preferred) / max(len(preferred_skills), 1)
            skill_score = (req_coverage * 0.8 + pref_coverage * 0.2) * 100
        elif not required_skills and not preferred_skills:
            skill_score = 50.0  # Neutral if no skills specified

        # Experience match (25% weight)
        exp_score = self._compute_experience_score(parsed_resume, job_description)

        # Education match (15% weight)
        edu_score = self._compute_education_score(parsed_resume, job_description)

        # Keyword density (10% weight)
        density_score = self._compute_keyword_density(parsed_resume, job_description)

        weighted_score = (
            skill_score * 0.50
            + exp_score * 0.25
            + edu_score * 0.15
            + density_score * 0.10
        )

        return {
            "score": round(weighted_score, 1),
            "matched_skills": matched + matched_preferred,
            "missing_skills": missing,
            "skill_coverage": round(len(matched) / max(len(required_skills), 1) * 100, 1),
            "experience_match": round(exp_score, 1),
            "education_match": round(edu_score, 1),
        }

    def _compute_experience_score(
        self, parsed_resume: Dict[str, Any], job_description: Dict[str, Any]
    ) -> float:
        """Score based on years of experience match."""
        resume_years = parsed_resume.get("total_years_experience") or 0.0
        min_years = job_description.get("min_years_experience")
        max_years = job_description.get("max_years_experience")

        if min_years is None:
            return 75.0  # Neutral when not specified

        if resume_years >= (min_years or 0):
            if max_years and resume_years > max_years * 1.5:
                return 70.0  # Overqualified penalty
            return 100.0
        else:
            deficit = min_years - resume_years
            return max(0.0, 100.0 - (deficit * 15))

    def _compute_education_score(
        self, parsed_resume: Dict[str, Any], job_description: Dict[str, Any]
    ) -> float:
        """Score based on education requirements."""
        edu_requirements = job_description.get("education_requirements") or []
        if not edu_requirements:
            return 75.0  # Neutral

        resume_edu = parsed_resume.get("education") or []
        resume_edu_text = " ".join([str(e) for e in resume_edu]).lower()

        degree_hierarchy = {"phd": 4, "master": 3, "bachelor": 2, "associate": 1}
        req_level = 0
        for deg in edu_requirements:
            for key, level in degree_hierarchy.items():
                if key in deg.lower():
                    req_level = max(req_level, level)

        resume_level = 0
        for key, level in degree_hierarchy.items():
            if key in resume_edu_text:
                resume_level = max(resume_level, level)

        if resume_level >= req_level:
            return 100.0
        elif resume_level == req_level - 1:
            return 70.0
        else:
            return 40.0

    def _compute_keyword_density(
        self, parsed_resume: Dict[str, Any], job_description: Dict[str, Any]
    ) -> float:
        """Score based on keyword density in resume vs job."""
        raw_text = (parsed_resume.get("raw_text") or "").lower()
        responsibilities = " ".join(job_description.get("responsibilities") or []).lower()

        if not responsibilities or not raw_text:
            return 50.0

        words = re.findall(r"\b[a-z]{3,}\b", responsibilities)
        stop_words = {
            "the", "and", "for", "with", "you", "will", "are", "our", "your",
            "have", "this", "that", "from", "they", "not", "but", "also",
        }
        keywords = [w for w in words if w not in stop_words]
        if not keywords:
            return 50.0

        matches = sum(1 for kw in keywords if kw in raw_text)
        return min(100.0, (matches / len(keywords)) * 200)  # Scale up to 100

    def _generate_recommendations(
        self,
        missing_skills: List[str],
        parsed_resume: Dict[str, Any],
        job_description: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on gaps."""
        recommendations = []

        # Skill recommendations
        for i, skill in enumerate(missing_skills[:5], 1):
            resource = self._get_learning_resource(skill)
            recommendations.append({
                "priority": i,
                "category": "skill",
                "title": f"Learn {skill.title()}",
                "description": f"This job requires {skill} which is not prominently featured in your resume.",
                "action": f"Complete a course or project using {skill}",
                "resource_url": resource,
            })

        # Experience recommendations
        resume_years = parsed_resume.get("total_years_experience") or 0
        min_years = job_description.get("min_years_experience")
        if min_years and resume_years < min_years:
            recommendations.append({
                "priority": len(missing_skills) + 1,
                "category": "experience",
                "title": "Build More Hands-on Experience",
                "description": f"This role requires {min_years} years experience. Consider contributing to open-source or building portfolio projects.",
                "action": "Create 2-3 projects demonstrating required skills",
                "resource_url": "https://github.com/explore",
            })

        # Resume wording recommendations
        if missing_skills:
            recommendations.append({
                "priority": len(missing_skills) + 2,
                "category": "resume",
                "title": "Tailor Resume Keywords",
                "description": "Incorporate the job's specific terminology in your resume bullet points.",
                "action": "Mirror the exact keywords from the job description",
                "resource_url": None,
            })

        return recommendations

    def _get_learning_resource(self, skill: str) -> Optional[str]:
        """Map skills to free learning resources."""
        resources = {
            "python": "https://docs.python.org/3/tutorial/",
            "react": "https://react.dev/learn",
            "docker": "https://docs.docker.com/get-started/",
            "kubernetes": "https://kubernetes.io/docs/tutorials/",
            "aws": "https://aws.amazon.com/training/",
            "machine learning": "https://www.coursera.org/learn/machine-learning",
            "tensorflow": "https://www.tensorflow.org/tutorials",
            "pytorch": "https://pytorch.org/tutorials/",
            "sql": "https://www.w3schools.com/sql/",
            "typescript": "https://www.typescriptlang.org/docs/",
            "fastapi": "https://fastapi.tiangolo.com/tutorial/",
            "django": "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
        }
        return resources.get(skill.lower(), f"https://www.coursera.org/search?query={skill.replace(' ', '+')}")
