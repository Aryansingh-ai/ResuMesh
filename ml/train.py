"""
ResuMesh ML Training Pipeline
Trains the match scoring model using collected feedback data.
"""

import os
import json
import pickle
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix,
)
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MatchingModelTrainer:
    """
    Trains resume-job matching models using feedback data.
    Tracks all experiments with MLflow.
    """

    def __init__(self, mlflow_uri: str = "http://localhost:5000"):
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment("resumesh-matching")
        self.scaler = StandardScaler()

    def load_data(self, data_path: str) -> pd.DataFrame:
        """Load training data from JSON file."""
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"Training data not found: {data_path}")

        with open(path) as f:
            records = json.load(f)

        df = pd.DataFrame(records)
        logger.info(f"Loaded {len(df)} training samples")
        return df

    def extract_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract feature matrix X and target vector y from raw data.

        Features:
        - skill_overlap_ratio: Ratio of matched to required skills
        - years_exp_ratio: Resume years / required years
        - education_score: Numeric education level match score
        - tech_stack_coverage: Tech stack coverage ratio
        - preferred_skill_overlap: Preferred skill overlap ratio
        - has_certifications: Binary flag
        - seniority_score: Numeric seniority mapping
        """
        feature_rows = []
        labels = []

        for _, row in df.iterrows():
            required_skills = set(row.get("required_skills", []))
            resume_skills = set(row.get("resume_skills", []))
            preferred_skills = set(row.get("preferred_skills", []))

            skill_overlap = len(required_skills & resume_skills) / max(len(required_skills), 1)
            preferred_overlap = len(preferred_skills & resume_skills) / max(len(preferred_skills), 1)

            resume_years = float(row.get("resume_years_exp", 0) or 0)
            required_years = float(row.get("required_years_exp", 0) or 1)
            exp_ratio = min(resume_years / max(required_years, 0.5), 2.0)

            edu_map = {"entry": 0, "associate": 1, "bachelor": 2, "master": 3, "phd": 4}
            resume_edu = edu_map.get(str(row.get("resume_education_level", "")).lower(), 2)
            required_edu = edu_map.get(str(row.get("required_education_level", "")).lower(), 2)
            edu_score = 1.0 if resume_edu >= required_edu else max(0.0, 1.0 - (required_edu - resume_edu) * 0.3)

            tech_stack = set(row.get("job_tech_stack", []))
            tech_coverage = len(tech_stack & resume_skills) / max(len(tech_stack), 1)

            has_certs = 1 if row.get("has_certifications", False) else 0

            seniority_map = {"entry": 0, "junior": 1, "mid": 2, "senior": 3}
            seniority_score = seniority_map.get(str(row.get("resume_seniority", "")).lower(), 1) / 3.0

            features = [
                skill_overlap,
                preferred_overlap,
                exp_ratio,
                edu_score,
                tech_coverage,
                has_certs,
                seniority_score,
                len(required_skills),
                len(resume_skills),
            ]
            feature_rows.append(features)

            # Label: 1 = good match, 0 = bad match
            feedback = str(row.get("feedback", "good_match")).lower()
            labels.append(1 if "good" in feedback else 0)

        X = np.array(feature_rows, dtype=np.float32)
        y = np.array(labels, dtype=np.int32)
        return X, y

    def train_all_models(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train multiple models and track with MLflow."""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        models = {
            "logistic_regression": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, random_state=42)),
            ]),
            "random_forest": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", RandomForestClassifier(
                    n_estimators=100, max_depth=10, random_state=42
                )),
            ]),
            "gradient_boosting": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", GradientBoostingClassifier(
                    n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42
                )),
            ]),
        }

        best_model = None
        best_f1 = -1
        results = {}

        for name, model in models.items():
            with mlflow.start_run(run_name=name):
                mlflow.log_param("model_type", name)
                mlflow.log_param("training_samples", len(X_train))
                mlflow.log_param("test_samples", len(X_test))

                # Train
                model.fit(X_train, y_train)

                # Evaluate
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1]

                accuracy = accuracy_score(y_test, y_pred)
                f1 = f1_score(y_test, y_pred, average="weighted")
                roc_auc = roc_auc_score(y_test, y_prob)
                cv_scores = cross_val_score(model, X, y, cv=5, scoring="f1_weighted")

                # Log metrics
                mlflow.log_metric("accuracy", accuracy)
                mlflow.log_metric("f1_score", f1)
                mlflow.log_metric("roc_auc", roc_auc)
                mlflow.log_metric("cv_f1_mean", cv_scores.mean())
                mlflow.log_metric("cv_f1_std", cv_scores.std())

                # Log model
                signature = infer_signature(X_train, y_pred)
                mlflow.sklearn.log_model(
                    model, "model", signature=signature, registered_model_name=f"resumesh-{name}"
                )

                results[name] = {
                    "model": model,
                    "accuracy": accuracy,
                    "f1": f1,
                    "roc_auc": roc_auc,
                    "cv_f1_mean": cv_scores.mean(),
                }

                logger.info(
                    f"Model: {name} | Accuracy: {accuracy:.3f} | F1: {f1:.3f} | AUC: {roc_auc:.3f}"
                )

                if f1 > best_f1:
                    best_f1 = f1
                    best_model = (name, model)

        return {
            "results": results,
            "best_model_name": best_model[0] if best_model else None,
            "best_model": best_model[1] if best_model else None,
            "best_f1": best_f1,
        }

    def save_model(self, model, model_path: str) -> None:
        """Save the best model to disk."""
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"Model saved to {model_path}")

    def run(self, data_path: str, model_output_path: str) -> Dict[str, Any]:
        """Full training pipeline."""
        logger.info("Starting ML training pipeline")

        df = self.load_data(data_path)
        X, y = self.extract_features(df)

        logger.info(f"Feature matrix: {X.shape}, Labels: {y.shape}, Positive rate: {y.mean():.2%}")

        results = self.train_all_models(X, y)

        if results["best_model"]:
            self.save_model(results["best_model"], model_output_path)

        logger.info(
            f"Training complete. Best model: {results['best_model_name']} with F1={results['best_f1']:.3f}"
        )
        return results


if __name__ == "__main__":
    import sys
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/training_data.json"
    model_path = sys.argv[2] if len(sys.argv) > 2 else "models/match_model.pkl"

    trainer = MatchingModelTrainer()
    trainer.run(data_path, model_path)
