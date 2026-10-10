"""Generic landing JSON-lines -> Bronze Parquet. Usage: bronze_json.py <lake> <source> <glob> [partition_col]

Rows are kept as-is (inferred schema) plus lineage columns. With a partition value
the target partition is overwritten, which makes reruns idempotent.
"""
import sys

from pyspark.sql import functions as F

from _common import session

lake, source, pattern = sys.argv[1:4]
part = sys.argv[4] if len(sys.argv) > 4 else None  # e.g. ds=2026-09-20

spark = session(f"bronze_{source}")
df = (spark.read.json(f"{lake}/landing/{pattern}")
      .withColumn("_source_file", F.input_file_name())
      .withColumn("_ingested_at", F.current_timestamp()))
out = f"{lake}/bronze/{source}"
if part:
    df = df.withColumn("ds", F.lit(part.split("=")[1]))
    df.write.mode("overwrite").partitionBy("ds").parquet(out)
else:
    df.write.mode("overwrite").parquet(out)
print(f"BRONZE {source}: {df.count()} rows")
spark.stop()
