"""Landing CSV -> Bronze Parquet for every Olist table. Raw strings, no cleaning."""
import glob
import os
import sys

from pyspark.sql import functions as F

from _common import session

lake = sys.argv[1]
spark = session("bronze_olist")

for path in sorted(glob.glob(f"{lake}/landing/olist/*.csv")):
    table = os.path.basename(path).replace("olist_", "").replace("_dataset.csv", "").replace(".csv", "")
    df = (spark.read.option("header", True).option("multiLine", True)
          .option("escape", '"').csv(path)  # all columns stay StringType in Bronze
          .withColumn("_source_file", F.lit(os.path.basename(path)))
          .withColumn("_ingested_at", F.current_timestamp()))
    df.write.mode("overwrite").parquet(f"{lake}/bronze/olist/{table}")
    print(f"BRONZE olist.{table}: {df.count()} rows")
spark.stop()
