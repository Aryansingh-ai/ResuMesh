-- =============================================================================
-- ResuMesh Database Initialization Script
-- =============================================================================

-- Create MLflow database
CREATE DATABASE mlflow;
-- Create Airflow database
CREATE DATABASE airflow;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mlflow TO resumesh_user;
GRANT ALL PRIVILEGES ON DATABASE airflow TO resumesh_user;
