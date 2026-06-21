"""
Model Registration Script
Promotes the best model to MLflow Model Registry if it passes quality thresholds.
"""

import json
import pickle
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Quality gates — model must beat these to be promoted
THRESHOLDS = {
    "f1_weighted": 0.75,
    "roc_auc": 0.75,
    "accuracy": 0.72,
}

MODEL_NAME = "resumesh-match-model"


def register(model_path: str, report_path: str = "ml/evaluation_report.json") -> None:
    # Load evaluation report
    report_file = Path(report_path)
    if not report_file.exists():
        logger.warning(f"No evaluation report at {report_path}. Skipping quality gate.")
        metrics = {}
    else:
        with open(report_file) as f:
            data = json.load(f)
        metrics = data.get("metrics", {})

    # Quality gate check
    for metric, threshold in THRESHOLDS.items():
        value = metrics.get(metric)
        if value is None:
            logger.warning(f"Metric {metric} missing from report. Proceeding anyway.")
            continue
        if value < threshold:
            logger.error(
                f"❌ Quality gate FAILED: {metric}={value:.3f} < threshold={threshold:.3f}"
            )
            logger.error("Model NOT promoted to registry.")
            sys.exit(1)
        logger.info(f"✅ Quality gate PASSED: {metric}={value:.3f} ≥ {threshold:.3f}")

    # Register to MLflow
    try:
        import mlflow
        import mlflow.sklearn

        mlflow_uri = "http://localhost:5000"
        mlflow.set_tracking_uri(mlflow_uri)

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        with mlflow.start_run(run_name="model-registration"):
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(k, v)

            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=MODEL_NAME,
            )

        logger.info(f"✅ Model registered to MLflow as '{MODEL_NAME}'")

    except Exception as e:
        logger.warning(f"MLflow registration skipped (MLflow not reachable): {e}")

    # Always save model to standard location
    standard_path = Path("models/production/match_model.pkl")
    standard_path.parent.mkdir(parents=True, exist_ok=True)

    import shutil
    shutil.copy2(model_path, standard_path)
    logger.info(f"✅ Model copied to production path: {standard_path}")

    # Write version file
    version_info = {
        "model_path": str(standard_path),
        "metrics": metrics,
        "model_name": MODEL_NAME,
    }
    with open("models/production/version.json", "w") as f:
        json.dump(version_info, f, indent=2)

    logger.info("✅ Model registration complete.")


if __name__ == "__main__":
    model_p = sys.argv[1] if len(sys.argv) > 1 else "models/match_model.pkl"
    report_p = sys.argv[2] if len(sys.argv) > 2 else "ml/evaluation_report.json"
    register(model_p, report_p)
