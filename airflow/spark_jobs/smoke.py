from _common import session

spark = session("smoke")
n = spark.range(1_000_000).selectExpr("sum(id) as s").first()["s"]
assert n == 499999500000, n
print("SMOKE_OK executors:", spark.sparkContext.defaultParallelism, "sum:", n)
spark.stop()
