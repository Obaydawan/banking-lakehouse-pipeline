"""
TransactSafe — Pipeline Orchestration DAG
============================================
Runs the full pipeline end-to-end on a daily schedule:
    1. Generate synthetic source data
    2. Load into bronze layer (DuckDB)
    3. Run dbt models (silver + gold layers)
    4. Run dbt tests (data quality validation)

Each task shells out to the project's Python venv, since dbt/duckdb/pandas
are installed there rather than inside the Airflow containers.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# This path is where the project is mounted INSIDE the Airflow containers
# (configured via the volume mount in docker-compose.yaml), not the host path.
PROJECT_ROOT = "/opt/transactsafe"

default_args = {
    "owner": "obaid",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="transactsafe_pipeline",
    description="Bronze -> Silver -> Gold fraud detection pipeline",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["transactsafe", "portfolio"],
) as dag:

    generate_data = BashOperator(
        task_id="generate_synthetic_data",
        bash_command=f"cd {PROJECT_ROOT}/data_generator && python generate_data.py",
    )

    load_bronze = BashOperator(
        task_id="load_bronze_layer",
        bash_command=f"cd {PROJECT_ROOT}/bronze && python load_bronze.py",
    )

    run_dbt_models = BashOperator(
        task_id="run_dbt_silver_gold",
        bash_command=f"cd {PROJECT_ROOT}/dbt_project/transactsafe && dbt run",
    )

    run_dbt_tests = BashOperator(
        task_id="run_dbt_tests",
        bash_command=f"cd {PROJECT_ROOT}/dbt_project/transactsafe && dbt test",
    )

    generate_data >> load_bronze >> run_dbt_models >> run_dbt_tests
