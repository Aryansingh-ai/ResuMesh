"""
Job Description Intelligence — Extracts structured data from raw job postings.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


# ── Skill keyword sets (shared with resume parser) ───────────────────────────
TECH_SKILLS = {
    # Programming
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "bash",
    # Frameworks
    "react", "angular", "vue", "nextjs", "django", "flask", "fastapi",
    "spring", "express", "graphql", "rest", "grpc",
    # ML/AI
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "scikit-learn", "pandas", "numpy", "langchain", "rag", "llm",
    # Cloud/DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
    "github actions", "jenkins",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "bigquery", "snowflake",
}

SOFT_SKILLS = {
    "communication", "teamwork", "leadership", "problem solving", "critical thinking",
    "time management", "adaptability", "creativity", "collaboration", "attention to detail",
    "project management", "agile", "scrum", "kanban",
}

SECTION_HEADERS = {
    "responsibilities": [
        "responsibilities", "what you'll do", "key responsibilities",
        "duties", "role overview", "you will",
    ],
    "qualifications": [
        "qualifications", "requirements", "what we're looking for",
        "required skills", "must have", "you have", "what you need",
    ],
    "preferred": [
        "preferred", "nice to have", "bonus", "plus", "desirable",
        "preferred qualifications",
    ],
    "education": ["education", "degree", "academic"],
    "benefits": ["benefits", "perks", "compensation", "what we offer"],
}


class JobDescriptionExtractor:
    """Extracts structured data from raw job description text."""

    def extract(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse raw job description text into a structured dictionary.

        Args:
            raw_text: The full text of a job posting.

        Returns:
            Structured dictionary with extracted fields.
        """
        if not raw_text or len(raw_text) < 50:
            raise ValueError("Job description text is too short to parse.")

        text_lower = raw_text.lower()
        sections = self._split_into_sections(raw_text)

        required_skills, preferred_skills = self._extract_skills(raw_text)
        min_exp, max_exp = self._extract_experience_range(raw_text)

        result = {
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "tech_stack": self._extract_tech_stack(raw_text),
            "soft_skills": self._extract_soft_skills(text_lower),
            "responsibilities": self._extract_bullets(sections.get("responsibilities", "")),
            "qualifications": self._extract_bullets(sections.get("qualifications", "")),
            "education_requirements": self._extract_education_requirements(raw_text),
            "certifications": self._extract_certifications(raw_text),
            "min_years_experience": min_exp,
            "max_years_experience": max_exp,
        }

        logger.bind(required_skills_count=len(required_skills).debug("Job description extracted"),
            preferred_skills_count=len(preferred_skills),
        )
        return result

    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """Split job description into logical sections."""
        sections: Dict[str, str] = {}
        lines = text.split("\n")
        current_section = "intro"
        current_lines: List[str] = []

        for line in lines:
            line_lower = line.lower().strip()
            matched_section = None

            for section_key, keywords in SECTION_HEADERS.items():
                if any(kw in line_lower for kw in keywords):
                    matched_section = section_key
                    break

            if matched_section:
                if current_lines:
                    sections[current_section] = "\n".join(current_lines)
                current_section = matched_section
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_section] = "\n".join(current_lines)

        return sections

    def _extract_skills(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract required and preferred skills."""
        text_lower = text.lower()

        # Split text around 'preferred' markers
        preferred_markers = re.search(
            r"(?:preferred|nice to have|bonus|plus).*?(?=\n{2,}|$)",
            text_lower,
            re.IGNORECASE | re.DOTALL,
        )

        preferred_text = preferred_markers.group(0) if preferred_markers else ""
        required_text = text_lower.replace(preferred_text, "")

        required_skills = [
            skill for skill in TECH_SKILLS
            if re.search(rf"\b{re.escape(skill)}\b", required_text)
        ]
        preferred_skills = [
            skill for skill in TECH_SKILLS
            if re.search(rf"\b{re.escape(skill)}\b", preferred_text)
            and skill not in required_skills
        ]

        return sorted(required_skills), sorted(preferred_skills)

    def _extract_tech_stack(self, text: str) -> List[str]:
        """Extract technical stack mentions."""
        text_lower = text.lower()
        return sorted([
            skill for skill in TECH_SKILLS
            if re.search(rf"\b{re.escape(skill)}\b", text_lower)
        ])

    def _extract_soft_skills(self, text_lower: str) -> List[str]:
        """Extract soft skills."""
        return sorted([
            skill for skill in SOFT_SKILLS
            if skill in text_lower
        ])

    def _extract_bullets(self, text: str) -> List[str]:
        """Extract bullet points from a section."""
        if not text:
            return []
        bullets = []
        for line in text.split("\n"):
            line = line.strip().lstrip("•-*·→▶ ")
            if len(line) > 10:
                bullets.append(line)
        return bullets[:20]  # Cap at 20 items

    def _extract_experience_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract minimum and maximum years of experience required."""
        patterns = [
            r"(\d+)\+?\s*(?:to|-)\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\+\s*(?:years?|yrs?)",
            r"minimum\s+of\s+(\d+)\s*(?:years?|yrs?)",
            r"at\s+least\s+(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\s*(?:years?|yrs?)\s+of\s+experience",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return float(groups[0]), float(groups[1])
                elif len(groups) == 1:
                    n = float(groups[0])
                    return n, n + 2.0
        return None, None

    def _extract_education_requirements(self, text: str) -> List[str]:
        """Extract education requirements."""
        degrees = []
        patterns = [
            r"\b(?:Bachelor'?s?|B\.?[Sc]|B\.?Tech|B\.?E)\b",
            r"\b(?:Master'?s?|M\.?[Sc]|M\.?Tech|M\.?B\.?A)\b",
            r"\bPh\.?D\b",
            r"\b(?:Associate'?s?)\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                degrees.append(re.search(pattern, text, re.IGNORECASE).group(0))
        return list(set(degrees))

    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certification requirements."""
        cert_patterns = [
            r"\bAWS\s+Certified\b[^\n]*",
            r"\bGoogle\s+Cloud\s+Professional\b[^\n]*",
            r"\bAzure\s+\w+\b[^\n]*",
            r"\bCKA\b",
            r"\bCKAD\b",
            r"\bPMP\b",
            r"\bCISSP\b",
            r"\bScrum\s+Master\b",
        ]
        certs = []
        for pattern in cert_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                certs.append(match.group(0).strip())
        return list(set(certs))
