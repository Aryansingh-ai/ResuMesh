"""
ML Model Evaluation Script
Generates a full evaluation report and registers the best model to MLflow.
"""

import json
import pickle
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix,
    precision_score, recall_score,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_model(model_path: str):
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    with open(path, "rb") as f:
        return pickle.load(f)


def extract_features_simple(records: list[dict]):
    """Quick feature extraction matching train.py logic."""
    rows = []
    labels = []
    for rec in records:
        required = set(rec.get("required_skills", []))
        resume = set(rec.get("resume_skills", []))
        preferred = set(rec.get("preferred_skills", []))
        tech = set(rec.get("job_tech_stack", []))

        skill_overlap = len(required & resume) / max(len(required), 1)
        preferred_overlap = len(preferred & resume) / max(len(preferred), 1)

        resume_years = float(rec.get("resume_years_exp", 0) or 0)
        req_years = float(rec.get("required_years_exp", 0) or 1)
        exp_ratio = min(resume_years / max(req_years, 0.5), 2.0)

        edu_map = {"entry": 0, "associate": 1, "bachelor": 2, "master": 3, "phd": 4}
        r_edu = edu_map.get(str(rec.get("resume_education_level", "")).lower(), 2)
        j_edu = edu_map.get(str(rec.get("required_education_level", "")).lower(), 2)
        edu_score = 1.0 if r_edu >= j_edu else max(0.0, 1.0 - (j_edu - r_edu) * 0.3)

        tech_cov = len(tech & resume) / max(len(tech), 1)
        has_certs = 1 if rec.get("has_certifications", False) else 0
        sen_map = {"entry": 0, "junior": 1, "mid": 2, "senior": 3}
        sen_score = sen_map.get(str(rec.get("resume_seniority", "")).lower(), 1) / 3.0

        rows.append([skill_overlap, preferred_overlap, exp_ratio, edu_score,
                     tech_cov, has_certs, sen_score,
                     len(required), len(resume)])
        labels.append(rec.get("label", 0))

    return np.array(rows, dtype=np.float32), np.array(labels, dtype=np.int32)


def evaluate(model_path: str, data_path: str, report_path: str) -> dict:
    model = load_model(model_path)

    with open(data_path) as f:
        records = json.load(f)

    X, y = extract_features_simple(records)
    logger.info(f"Evaluating on {len(X)} samples")

    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "f1_weighted": float(f1_score(y, y_pred, average="weighted")),
        "f1_binary": float(f1_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred, zero_division=0)),
        "recall": float(recall_score(y, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, y_prob)),
        "n_samples": len(X),
        "positive_rate": float(y.mean()),
        "model_path": model_path,
        "data_path": data_path,
    }

    cm = confusion_matrix(y, y_pred).tolist()
    report = classification_report(y, y_pred, output_dict=True)

    full_report = {
        "metrics": metrics,
        "confusion_matrix": cm,
        "classification_report": report,
    }

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(full_report, f, indent=2)

    logger.info(f"Evaluation complete:")
    logger.info(f"  Accuracy:  {metrics['accuracy']:.3f}")
    logger.info(f"  F1 Score:  {metrics['f1_weighted']:.3f}")
    logger.info(f"  ROC-AUC:   {metrics['roc_auc']:.3f}")
    logger.info(f"  Saved report → {report_path}")

    return metrics


if __name__ == "__main__":
    model_p = sys.argv[1] if len(sys.argv) > 1 else "models/match_model.pkl"
    data_p = sys.argv[2] if len(sys.argv) > 2 else "data/processed/training_data.json"
    report_p = sys.argv[3] if len(sys.argv) > 3 else "ml/evaluation_report.json"
    evaluate(model_p, data_p, report_p)
