"""One-time/manual: Olist (real marketplace data) + FX history -> Bronze."""
from datetime import datetime

from airflow import DAG
from airflow.datasets import Dataset
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from include import config, ingest

OLIST_BRONZE = Dataset("lake://bronze/olist")
FX_BRONZE = Dataset("lake://bronze/fx_rates")

with DAG("olist_bronze_ingest", start_date=datetime(2026, 1, 1), schedule=None, catchup=False,
         tags=["ingest", "bronze", "real-data"], max_active_runs=1) as dag:
    download = PythonOperator(task_id="download_olist", python_callable=ingest.download_olist,
                              retries=2)
    to_bronze = SparkSubmitOperator(
        task_id="olist_to_bronze", application=f"{config.JOBS}/bronze_olist.py",
        application_args=[config.LAKE], conn_id="spark_default", conf=config.SPARK_CONF,
        outlets=[OLIST_BRONZE])
    # Historical BRL/USD rates for the period Olist covers (used to show prices in USD).
    fx_hist = PythonOperator(
        task_id="download_fx_history",
        python_callable=lambda: ingest.fetch_fx(*config.OLIST_FX_RANGE, out_name="history"))
    fx_bronze = SparkSubmitOperator(
        task_id="fx_history_to_bronze", application=f"{config.JOBS}/bronze_json.py",
        application_args=[config.LAKE, "fx_rates", "fx/history.json", "ds=history"],
        conn_id="spark_default", conf=config.SPARK_CONF, outlets=[FX_BRONZE])
    download >> to_bronze
    fx_hist >> fx_bronze
