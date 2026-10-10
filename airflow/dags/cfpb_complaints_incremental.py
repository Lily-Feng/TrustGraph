"""Daily incremental pull of CFPB consumer complaints (real, public, no key).

One run == one `date_received` day, so backfills and reruns are idempotent
(landing file and Bronze partition are both overwritten per day).
"""
from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include import config, ingest

with DAG("cfpb_complaints_incremental", start_date=datetime(2026, 9, 20), schedule="@daily",
         catchup=True, max_active_runs=2, tags=["ingest", "bronze", "real-data"],
         default_args={"retries": 2}) as dag:
    extract = PythonOperator(task_id="extract_day", python_callable=ingest.fetch_cfpb_day,
                             op_kwargs={"ds": "{{ ds }}"})
    to_bronze = SparkSubmitOperator(
        task_id="to_bronze", application=f"{config.JOBS}/bronze_json.py",
        application_args=[config.LAKE, "cfpb_complaints", "cfpb/ds={{ ds }}/complaints.json", "ds={{ ds }}"],
        conn_id="spark_default", conf=config.SPARK_CONF,
        outlets=[Dataset("lake://bronze/cfpb_complaints")])
    extract >> to_bronze
