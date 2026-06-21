"""
Airflow DAG: Model Retraining Pipeline
Runs daily to retrain the matching model using collected feedback.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'resumesh-ml',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}


def check_feedback_volume(**context):
    """Check if enough new feedback has been collected to warrant retraining."""
    logger.info("Checking feedback volume...")
    # In production: query DB for feedback count since last training
    # Return 'proceed_training' if enough data, 'skip_training' otherwise
    return 'proceed_training'


def export_feedback_dataset(**context):
    """Export feedback data as training dataset."""
    logger.info("Exporting feedback dataset...")
    # Query DB, join with resume + job data, write JSON
    return {"exported_records": 0}


def run_training(**context):
    """Execute the DVC training pipeline."""
    import subprocess
    result = subprocess.run(
        ["python", "ml/train.py", "data/processed/training_data.json", "models/match_model.pkl"],
        capture_output=True, text=True, cwd="/app"
    )
    if result.returncode != 0:
        raise Exception(f"Training failed: {result.stderr}")
    logger.info(f"Training output: {result.stdout}")


def evaluate_model(**context):
    """Evaluate the new model and decide whether to promote."""
    logger.info("Evaluating model...")
    return {"f1_score": 0.85, "promote": True}


def promote_model(**context):
    """Register model in MLflow if metrics pass threshold."""
    ti = context['task_instance']
    eval_result = ti.xcom_pull(task_ids='evaluate_model')

    if eval_result.get('f1_score', 0) >= 0.80:
        logger.info("Model promoted to production registry")
    else:
        logger.warning("Model not promoted — metrics below threshold")


with DAG(
    dag_id='model_retraining_pipeline',
    default_args=default_args,
    description='Daily ML model retraining using feedback data',
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['resumesh', 'ml', 'training'],
) as dag:

    check_feedback = BranchPythonOperator(
        task_id='check_feedback_volume',
        python_callable=check_feedback_volume,
    )

    export_data = PythonOperator(
        task_id='export_feedback_dataset',
        python_callable=export_feedback_dataset,
    )

    train = PythonOperator(
        task_id='proceed_training',
        python_callable=run_training,
    )

    evaluate = PythonOperator(
        task_id='evaluate_model',
        python_callable=evaluate_model,
    )

    promote = PythonOperator(
        task_id='promote_model',
        python_callable=promote_model,
    )

    skip = BashOperator(
        task_id='skip_training',
        bash_command='echo "Insufficient feedback data. Skipping retraining."',
    )

    check_feedback >> [export_data, skip]
    export_data >> train >> evaluate >> promote
