"""Bronze -> Silver -> Gold -> JSON export for the TrustGraph demo, with DQ gates between layers.

Runs whenever ANY upstream ingest DAG updates its Bronze dataset (data-aware scheduling).
"""
from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include import config

olist = Dataset("lake://bronze/olist")
cfpb = Dataset("lake://bronze/cfpb_complaints")
fx = Dataset("lake://bronze/fx_rates")
stripe = Dataset("lake://bronze/stripe_events_raw")


def job(task_id, script, *args, **kw):
    return SparkSubmitOperator(task_id=task_id, application=f"{config.JOBS}/{script}",
                               application_args=[config.LAKE, *args], conn_id="spark_default",
                               conf=config.SPARK_CONF, **kw)


with DAG("mdt_build_gold", start_date=datetime(2026, 1, 1), schedule=(olist | cfpb | fx | stripe),
         catchup=False, max_active_runs=1, tags=["transform", "gold"]) as dag:
    dq_bronze = job("dq_bronze", "dq_check.py", "bronze")
    silver = job("build_silver", "silver_build.py")
    dq_silver = job("dq_silver", "dq_check.py", "silver")
    gold = job("build_gold", "gold_mdt.py")
    dq_gold = job("dq_gold", "dq_check.py", "gold")
    export = job("export_json", "export_json.py", config.EXPORT)
    dq_bronze >> silver >> dq_silver >> gold >> dq_gold >> export
