"""
Prometheus metrics setup for ResuMesh FastAPI backend.
"""

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response
import structlog

logger = structlog.get_logger(__name__)

# ── Custom Metrics ────────────────────────────────────────────────────────────
resume_uploads_total = Counter(
    "resumesh_resume_uploads_total",
    "Total number of resume uploads",
    ["status"],
)

job_analyses_total = Counter(
    "resumesh_job_analyses_total",
    "Total number of job analyses performed",
    ["portal", "status"],
)

match_score_histogram = Histogram(
    "resumesh_match_score",
    "Distribution of resume-job match scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

cover_letter_generations_total = Counter(
    "resumesh_cover_letter_generations_total",
    "Total cover letters generated",
    ["status"],
)

rag_queries_total = Counter(
    "resumesh_rag_queries_total",
    "Total RAG career coach queries",
    ["status"],
)

active_users_gauge = Gauge(
    "resumesh_active_users",
    "Number of active user sessions",
)

ml_prediction_duration = Histogram(
    "resumesh_ml_prediction_duration_seconds",
    "Duration of ML model predictions",
    ["model_version"],
)

feedback_collected_total = Counter(
    "resumesh_feedback_collected_total",
    "Total feedback entries collected",
    ["feedback_type"],
)


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus instrumentation and metrics endpoint to the app."""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/ready", "/metrics"],
        inprogress_labels=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    logger.info("Prometheus metrics configured at /metrics")
