"""Bronze -> Silver: typing, dedupe, quarantine, unit normalisation. Usage: silver_build.py <lake>"""
import sys

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from _common import session

lake = sys.argv[1]
spark = session("silver_build")
B = lambda p: spark.read.parquet(f"{lake}/bronze/{p}")


def write(df, name):
    df.write.mode("overwrite").parquet(f"{lake}/silver/{name}")
    print(f"SILVER {name}: {df.count()} rows")


# ---------------- Olist ----------------
ts = lambda c: F.to_timestamp(F.col(c))
write(B("olist/orders").select(
    "order_id", "customer_id", "order_status",
    ts("order_purchase_timestamp").alias("purchased_at"),
    ts("order_approved_at").alias("approved_at"),
    ts("order_delivered_carrier_date").alias("carrier_at"),
    ts("order_delivered_customer_date").alias("delivered_at"),
    ts("order_estimated_delivery_date").alias("estimated_at")).dropDuplicates(["order_id"]), "olist_orders")

write(B("olist/order_items").select(
    "order_id", F.col("order_item_id").cast("int").alias("item_no"), "product_id", "seller_id",
    ts("shipping_limit_date").alias("ship_by"),
    F.col("price").cast("double").alias("price_brl"),
    F.col("freight_value").cast("double").alias("freight_brl")), "olist_order_items")

# reviews: review_id is not unique in the source -> keep the latest answer per (review_id, order_id)
w = Window.partitionBy("review_id", "order_id").orderBy(F.col("review_answer_timestamp").desc())
write(B("olist/order_reviews").withColumn("rn", F.row_number().over(w)).filter("rn = 1").select(
    "review_id", "order_id", F.col("review_score").cast("int").alias("score"),
    ts("review_creation_date").alias("created_at"), ts("review_answer_timestamp").alias("answered_at")),
    "olist_reviews")

cat = B("olist/product_category_name_translation").select(
    "product_category_name", F.col("product_category_name_english").alias("category"))
write(B("olist/products").select("product_id", "product_category_name")
      .join(cat, "product_category_name", "left")
      .select("product_id", F.coalesce("category", F.lit("unknown")).alias("category")), "olist_products")

write(B("olist/sellers").select("seller_id", F.col("seller_city").alias("city"), F.col("seller_state").alias("state")),
      "olist_sellers")

# ---------------- CFPB ----------------
w = Window.partitionBy("complaint_id").orderBy(F.col("_ingested_at").desc())
write(B("cfpb_complaints").withColumn("rn", F.row_number().over(w)).filter("rn = 1").select(
    "complaint_id", "company", "product", "issue", "state", "submitted_via", "company_response",
    (F.col("timely") == "Yes").alias("timely"),
    F.to_date(F.col("date_received")).alias("received_on")), "cfpb_complaints")

# ---------------- FX ----------------
w = Window.partitionBy("date", "currency").orderBy(F.col("_ingested_at").desc())
write(B("fx_rates").withColumn("rn", F.row_number().over(w)).filter("rn = 1").select(
    F.to_date("date").alias("date"), "base", "currency", F.col("rate").cast("double").alias("rate")), "fx_rates")

# ---------------- Stripe (the data-contract quirks) ----------------
KNOWN_API_VERSIONS = ["2023-10-16", "2024-06-20", "2025-03-31"]
CURRENCY_EXPONENT = {"usd": 2, "eur": 2, "gbp": 2, "brl": 2, "jpy": 0}   # zero-decimal currencies

raw = B("stripe_events_raw")
# quirk 3: unknown api_version -> quarantine, never fail the batch
rejected = raw.filter(~F.col("api_version").isin(KNOWN_API_VERSIONS)) \
              .withColumn("_reject_reason", F.lit("unknown_api_version"))
rejected.write.mode("overwrite").parquet(f"{lake}/silver/_rejected/stripe_events")
print(f"SILVER _rejected/stripe_events: {rejected.count()} rows")

# quirk 1: at-least-once delivery -> dedupe on event_id (keep first receipt)
w = Window.partitionBy("event_id").orderBy(F.col("ingested_at").asc())
good = (raw.filter(F.col("api_version").isin(KNOWN_API_VERSIONS))
        .withColumn("rn", F.row_number().over(w)).filter("rn = 1").drop("rn"))

schema = T.StructType([T.StructField(n, t) for n, t in [
    ("object", T.StringType()), ("id", T.StringType()), ("amount", T.LongType()),
    ("currency", T.StringType()), ("on_behalf_of", T.StringType()),
    ("initiation_channel", T.StringType()), ("mandate_id", T.StringType()),
    ("mandate_violation", T.BooleanType()), ("payment_intent", T.StringType()),
    ("risk_score", T.IntegerType()), ("charge", T.StringType()), ("reason", T.StringType())]])
p = good.withColumn("o", F.from_json("payload", schema))

# quirk 4: integer minor units -> decimal using an explicit exponent table (never a naive /100)
exp_map = F.create_map(*[x for k, v in CURRENCY_EXPONENT.items() for x in (F.lit(k), F.lit(v))])
silver = p.select(
    "event_id", "event_type", "api_version", F.col("created"), "ingested_at",
    F.col("o.id").alias("object_id"), F.col("o.on_behalf_of").alias("account_id"),
    F.col("o.initiation_channel").alias("initiation_channel"),
    F.col("o.mandate_id").alias("mandate_id"),
    F.coalesce("o.mandate_violation", F.lit(False)).alias("mandate_violation"),
    F.col("o.payment_intent").alias("payment_intent_id"), F.col("o.charge").alias("charge_id"),
    F.col("o.reason").alias("dispute_reason"), F.col("o.risk_score").alias("risk_score"),
    F.col("o.currency").alias("currency"), F.col("o.amount").alias("amount_minor"),
    (F.col("o.amount") / F.pow(F.lit(10), exp_map[F.col("o.currency")])).alias("amount"),
    F.to_date("created").alias("created_on"))
# quirk 2: out-of-order arrival is handled by always ordering on `created`, never `ingested_at`;
# a dispute whose parent charge has not landed yet is kept (no FK enforcement in Silver).
write(silver, "stripe_events")
spark.stop()
