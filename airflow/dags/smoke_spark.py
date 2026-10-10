"""Manual DAG proving Airflow -> Spark cluster wiring works."""
from datetime import datetime

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include import config

with DAG("smoke_spark", start_date=datetime(2026, 1, 1), schedule=None, catchup=False,
         tags=["infra"]):
    SparkSubmitOperator(task_id="spark_sum", application=f"{config.JOBS}/smoke.py",
                        conn_id="spark_default", conf=config.SPARK_CONF, verbose=False)
