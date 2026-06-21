"""
Airflow DAG: Resume Processing Pipeline
Triggers when a new resume is uploaded.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.http import SimpleHttpOperator
import requests
import logging

logger = logging.getLogger(__name__)

BACKEND_URL = "{{ var.value.get('backend_url', 'http://backend:8000') }}"

default_args = {
    'owner': 'resumesh',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def check_unprocessed_resumes(**context):
    """Check for resumes that haven't been parsed yet."""
    try:
        # This would normally call a privileged admin API
        response = requests.get(
            f"{BACKEND_URL}/api/v1/admin/stats",
            headers={"Authorization": "Bearer {{ var.value.get('admin_token', '') }}"},
            timeout=30,
        )
        logger.info(f"System stats: {response.json()}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to check resumes: {e}")
        return {}


def run_embedding_refresh(**context):
    """Refresh embeddings for recently updated resumes."""
    logger.info("Refreshing resume embeddings...")
    # In production this would call internal services
    return {"status": "completed"}


with DAG(
    dag_id='resume_processing_pipeline',
    default_args=default_args,
    description='Process and embed new resumes',
    schedule_interval='*/30 * * * *',  # Every 30 minutes
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['resumesh', 'ml', 'processing'],
) as dag:

    check_resumes = PythonOperator(
        task_id='check_unprocessed_resumes',
        python_callable=check_unprocessed_resumes,
    )

    refresh_embeddings = PythonOperator(
        task_id='refresh_embeddings',
        python_callable=run_embedding_refresh,
    )

    check_resumes >> refresh_embeddings
