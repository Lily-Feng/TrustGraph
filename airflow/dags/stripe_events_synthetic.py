"""Daily synthetic Stripe-shaped webhook events -> bronze.stripe_events_raw.

Real public data for agent-initiated payments does not exist, so this is generated to
spec/data-contract.md. Needs Olist Bronze first (it reuses seller ids as Connect accounts).
"""
from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include import config

with DAG("stripe_events_synthetic", start_date=datetime(2026, 9, 20), schedule="@daily",
         catchup=True, max_active_runs=1, tags=["ingest", "bronze", "synthetic"]) as dag:
    SparkSubmitOperator(
        task_id="generate_events", application=f"{config.JOBS}/gen_stripe_events.py",
        application_args=[config.LAKE, "{{ ds }}", "30000"], conn_id="spark_default",
        conf=config.SPARK_CONF, outlets=[Dataset("lake://bronze/stripe_events_raw")])
