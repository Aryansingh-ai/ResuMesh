"""
ML Preprocessing / Parsing Script
Converts raw feedback JSON into a clean training dataset.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def normalize_skill(skill: str) -> str:
    """Lowercase and strip a skill name."""
    return skill.strip().lower()


def parse_records(records: list[dict]) -> list[dict]:
    """
    Clean and normalize raw feedback records into training-ready format.
    Handles missing values, normalizes skill lists, and validates labels.
    """
    cleaned = []
    skipped = 0

    for rec in records:
        feedback_type = str(rec.get("feedback_type", "")).lower()

        # Only keep binary good/bad labels
        if "good" not in feedback_type and "bad" not in feedback_type:
            skipped += 1
            continue

        required_skills = [normalize_skill(s) for s in (rec.get("required_skills") or []) if s]
        preferred_skills = [normalize_skill(s) for s in (rec.get("preferred_skills") or []) if s]
        resume_skills = [normalize_skill(s) for s in (rec.get("resume_skills") or []) if s]
        tech_stack = [normalize_skill(s) for s in (rec.get("job_tech_stack") or []) if s]

        if not required_skills and not resume_skills:
            skipped += 1
            continue

        cleaned.append({
            "feedback_type": feedback_type,
            "label": 1 if "good" in feedback_type else 0,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "resume_skills": resume_skills,
            "job_tech_stack": tech_stack,
            "resume_years_exp": float(rec.get("resume_years_exp") or 0),
            "required_years_exp": float(rec.get("required_years_exp") or 0),
            "resume_seniority": str(rec.get("resume_seniority") or "mid").lower(),
            "has_certifications": bool(rec.get("has_certifications", False)),
            "resume_education_level": str(rec.get("resume_education_level") or "bachelor").lower(),
            "required_education_level": str(rec.get("required_education_level") or "bachelor").lower(),
        })

    logger.info(f"Parsed {len(cleaned)} valid records, skipped {skipped}")
    return cleaned


def run(input_path: str, output_path: str) -> None:
    inp = Path(input_path)
    if not inp.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    with open(inp) as f:
        records = json.load(f)

    logger.info(f"Loaded {len(records)} raw records from {input_path}")

    cleaned = parse_records(records)

    # Class balance report
    pos = sum(r["label"] for r in cleaned)
    neg = len(cleaned) - pos
    logger.info(f"Class distribution — positive: {pos} ({pos/max(len(cleaned),1):.1%}), negative: {neg}")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(cleaned, f, indent=2)

    logger.info(f"Saved {len(cleaned)} processed records → {output_path}")


if __name__ == "__main__":
    import sys
    inp = sys.argv[1] if len(sys.argv) > 1 else "data/raw/feedback.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/processed/training_data.json"
    run(inp, out)
