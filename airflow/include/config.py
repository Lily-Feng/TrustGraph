"""Shared paths, URLs and Spark settings for TrustGraph DAGs."""
import os

LAKE = os.environ.get("TRUSTGRAPH_LAKE", "/opt/airflow/lake")
EXPORT = os.environ.get("TRUSTGRAPH_EXPORT", "/opt/airflow/export")
JOBS = "/opt/airflow/spark_jobs"

LANDING = f"{LAKE}/landing"
BRONZE = f"{LAKE}/bronze"
SILVER = f"{LAKE}/silver"
GOLD = f"{LAKE}/gold"

# Public, no-auth mirror of the original Olist Kaggle files (byte sizes match the originals).
OLIST_BASE = "https://huggingface.co/datasets/bulutttt/olist-raw-data/resolve/main"
OLIST_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_customers_dataset.csv",
    "product_category_name_translation.csv",
]
OLIST_FX_RANGE = ("2016-09-01", "2018-10-31")  # period covered by Olist orders

CFPB_API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
FX_API = "https://api.frankfurter.dev/v1"

SPARK_CONF = {
    "spark.driver.host": "airflow-scheduler",
    "spark.driver.bindAddress": "0.0.0.0",
    "spark.driver.memory": "1g",
    "spark.executor.memory": "1500m",
    "spark.cores.max": "2",
    "spark.sql.shuffle.partitions": "8",
    "spark.sql.session.timeZone": "UTC",
    "spark.sql.sources.partitionOverwriteMode": "dynamic",
    "spark.ui.showConsoleProgress": "false",
}
