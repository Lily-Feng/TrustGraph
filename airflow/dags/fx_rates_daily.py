"""Daily FX rates (Frankfurter, ECB-based, no key) -> Bronze."""
from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include import config, ingest

with DAG("fx_rates_daily", start_date=datetime(2026, 9, 20), schedule="@daily", catchup=True,
         max_active_runs=2, tags=["ingest", "bronze", "real-data"],
         default_args={"retries": 2}) as dag:
    extract = PythonOperator(
        task_id="extract_day",
        python_callable=lambda ds: ingest.fetch_fx(ds, ds, out_name=f"day_{ds}"),
        op_kwargs={"ds": "{{ ds }}"})
    # ECB publishes business days only; weekend runs return an empty file -> job tolerates it.
    to_bronze = SparkSubmitOperator(
        task_id="to_bronze", application=f"{config.JOBS}/bronze_json.py",
        application_args=[config.LAKE, "fx_rates", "fx/day_{{ ds }}.json", "ds={{ ds }}"],
        conn_id="spark_default", conf=config.SPARK_CONF,
        outlets=[Dataset("lake://bronze/fx_rates")])
    extract >> to_bronze
