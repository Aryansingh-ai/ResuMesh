"""
ML Features Script
Extracts and saves feature matrix + feature names for reproducibility.
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

FEATURE_NAMES = [
    "skill_overlap_ratio",
    "preferred_skill_overlap_ratio",
    "experience_ratio",
    "education_score",
    "tech_stack_coverage",
    "has_certifications",
    "seniority_score",
    "n_required_skills",
    "n_resume_skills",
]


def build_features(records: list[dict]):
    """Build numpy feature matrix matching train.py logic."""
    rows = []
    labels = []

    for rec in records:
        required = set(rec.get("required_skills", []))
        resume = set(rec.get("resume_skills", []))
        preferred = set(rec.get("preferred_skills", []))
        tech = set(rec.get("job_tech_stack", []))

        skill_overlap = len(required & resume) / max(len(required), 1)
        preferred_overlap = len(preferred & resume) / max(len(preferred), 1)

        resume_yrs = float(rec.get("resume_years_exp", 0) or 0)
        req_yrs = float(rec.get("required_years_exp", 0) or 1)
        exp_ratio = min(resume_yrs / max(req_yrs, 0.5), 2.0)

        edu_map = {"entry": 0, "associate": 1, "bachelor": 2, "master": 3, "phd": 4}
        r_edu = edu_map.get(str(rec.get("resume_education_level", "")).lower(), 2)
        j_edu = edu_map.get(str(rec.get("required_education_level", "")).lower(), 2)
        edu_score = 1.0 if r_edu >= j_edu else max(0.0, 1.0 - (j_edu - r_edu) * 0.3)

        tech_cov = len(tech & resume) / max(len(tech), 1)
        has_certs = 1 if rec.get("has_certifications", False) else 0

        sen_map = {"entry": 0, "junior": 1, "mid": 2, "senior": 3}
        sen = sen_map.get(str(rec.get("resume_seniority", "")).lower(), 1) / 3.0

        rows.append([skill_overlap, preferred_overlap, exp_ratio, edu_score,
                     tech_cov, has_certs, sen, len(required), len(resume)])
        labels.append(rec.get("label", 0))

    X = np.array(rows, dtype=np.float32)
    y = np.array(labels, dtype=np.int32)
    return X, y


def run(data_path: str, features_path: str, names_path: str) -> None:
    with open(data_path) as f:
        records = json.load(f)

    X, y = build_features(records)
    logger.info(f"Built feature matrix: {X.shape}, labels: {y.shape}")

    Path(features_path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(features_path, X=X, y=y)

    with open(names_path, "w") as f:
        json.dump(FEATURE_NAMES, f, indent=2)

    logger.info(f"Saved features → {features_path}")
    logger.info(f"Saved feature names → {names_path}")


if __name__ == "__main__":
    dp = sys.argv[1] if len(sys.argv) > 1 else "data/processed/training_data.json"
    fp = sys.argv[2] if len(sys.argv) > 2 else "data/processed/features.npz"
    np_ = sys.argv[3] if len(sys.argv) > 3 else "data/processed/feature_names.json"
    run(dp, fp, np_)
