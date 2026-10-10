"""Synthetic Stripe-shaped webhook events -> bronze/stripe_events_raw (one day per run).

Follows spec/data-contract.md section 3: raw envelope, payload kept as an unparsed JSON
string, and the four quirks injected on purpose so Silver has real work to do:
  1. at-least-once delivery  -> ~3% of events are re-delivered
  2. out-of-order arrival    -> ingested_at is not monotonic with created
  3. API-version drift       -> 3 known versions + a rare unknown one (quarantined in Silver)
  4. integer minor units     -> mixed 2-decimal and zero-decimal (JPY) currencies

Connect accounts reuse Olist seller ids so Gold can join payment risk to merchants.
This is SYNTHETIC data; every row has livemode=false and an _origin of 'synthetic'.
Usage: gen_stripe_events.py <lake> <ds> <n_payments>
"""
import sys

from pyspark.sql import functions as F

from _common import session

lake, ds, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
spark = session("gen_stripe_events")

sellers = (spark.read.parquet(f"{lake}/bronze/olist/sellers").select("seller_id")
           .withColumn("acct", F.concat(F.lit("acct_"), F.substring(F.col("seller_id"), 1, 16)))
           .withColumn("sidx", F.row_number().over(__import__("pyspark.sql.window", fromlist=["Window"]).Window.orderBy("seller_id")) - 1))
n_sellers = sellers.count()

seed = int(ds.replace("-", ""))
base = spark.range(n).withColumn("r", F.rand(seed)).withColumn("r2", F.rand(seed + 1)).withColumn("r3", F.rand(seed + 2))
# a skewed merchant choice (some merchants are busier) + a small "risky" merchant tail
base = base.withColumn("sidx", (F.pow(F.col("r"), F.lit(1.6)) * n_sellers).cast("long"))
base = base.join(F.broadcast(sellers), "sidx")
risky = (F.col("sidx") % 23 == 0)

ccy = F.when(F.col("r2") < 0.70, "usd").when(F.col("r2") < 0.85, "eur").when(F.col("r2") < 0.95, "gbp").otherwise("jpy")
channel = (F.when(F.col("r3") < 0.62, "human_initiated")
            .when(F.col("r3") < 0.90, "agent_delegated").otherwise("agent_to_agent"))
amount_major = F.when(F.col("r3") >= 0.90, F.round(F.rand(seed + 3) * 0.5, 4)) \
                .otherwise(F.round(F.exp(F.rand(seed + 4) * 5 + 2), 2))
pay = (base.withColumn("currency", ccy).withColumn("channel", channel)
       .withColumn("amount", F.when(F.col("currency") == "jpy", F.round(amount_major * 110).cast("long"))
                   .otherwise(F.round(amount_major * 100).cast("long")))   # integer minor units
       .withColumn("t0", F.to_timestamp(F.lit(ds)) + (F.rand(seed + 5) * 86399).cast("int") * F.expr("interval 1 second"))
       .withColumn("pi", F.concat(F.lit("pi_"), F.substring(F.sha2(F.concat(F.lit(ds), F.col("id").cast("string")), 256), 1, 24)))
       .withColumn("ch", F.concat(F.lit("ch_"), F.substring(F.sha2(F.col("pi"), 256), 1, 24)))
       .withColumn("mandate", F.when(F.col("channel") != "human_initiated",
                                     F.concat(F.lit("mand_"), F.substring(F.sha2(F.col("pi"), 256), 1, 10))))
       .withColumn("over_mandate", (F.col("channel") == "agent_delegated") & (F.rand(seed + 6) < F.when(risky, 0.12).otherwise(0.01)))
       .withColumn("fraud", F.rand(seed + 7) < F.when(risky, 0.06).otherwise(0.004))
       .withColumn("blocked", F.rand(seed + 8) < 0.04))


def payload(obj_type, id_col, extra):
    return F.to_json(F.struct(
        F.lit("event").alias("object"),
        F.struct(F.lit(obj_type).alias("object"), id_col.alias("id"), *extra).alias("data_object")))


def mk(df, etype, ts, prefix, obj_id, extra_fields):
    """Wrap an object into a webhook envelope; evt id derived from object id + type (deterministic)."""
    obj = F.to_json(F.struct(F.lit(etype.split(".")[0]).alias("object"), obj_id.alias("id"), *extra_fields))
    return df.select(
        F.concat(F.lit("evt_"), F.substring(F.sha2(F.concat(obj_id, F.lit(etype)), 256), 1, 24)).alias("event_id"),
        F.lit(etype).alias("event_type"),
        F.when(F.rand(seed + 9) < 0.01, F.lit("2099-01-01.unknown"))          # unknown shape
         .when(F.rand(seed + 10) < 0.25, F.lit("2023-10-16"))
         .when(F.rand(seed + 11) < 0.40, F.lit("2024-06-20"))
         .otherwise(F.lit("2025-03-31")).alias("api_version"),
        ts.alias("created"),
        F.concat(F.lit("req_"), F.substring(F.sha2(obj_id, 256), 1, 14)).alias("request_id"),
        F.concat(F.lit("idem_"), F.substring(F.sha2(F.concat(obj_id, F.lit(etype)), 256), 1, 14)).alias("idempotency_key"),
        F.lit(False).alias("livemode"),
        obj.alias("payload"),
        (F.col("t0") + (F.rand(seed + 12) * 600 - 30).cast("int") * F.expr("interval 1 second")).alias("ingested_at"))  # skew => out-of-order


common = lambda: [F.col("amount").alias("amount"), F.col("currency").alias("currency"),
                  F.col("acct").alias("on_behalf_of"), F.col("channel").alias("initiation_channel"),
                  F.col("mandate").alias("mandate_id"), F.col("over_mandate").alias("mandate_violation")]

created_pi = F.col("t0")
ok = pay.filter(~F.col("blocked"))
events = mk(pay, "payment_intent.created", created_pi, "pi", F.col("pi"), common())
events = events.unionByName(mk(ok, "payment_intent.succeeded", F.col("t0") + F.expr("interval 2 seconds"), "pi", F.col("pi"), common()))
events = events.unionByName(mk(pay.filter(F.col("blocked")), "payment_intent.canceled", F.col("t0") + F.expr("interval 1 seconds"), "pi", F.col("pi"), common()))
events = events.unionByName(mk(ok, "charge.succeeded", F.col("t0") + F.expr("interval 2 seconds"), "ch", F.col("ch"),
                               common() + [F.col("pi").alias("payment_intent"),
                                           F.round(F.rand(seed + 13) * 99).cast("int").alias("risk_score")]))
# disputes: fraud-driven, plus friendly-fraud noise on human checkouts. Created days later (late arrival vs charge).
disp = ok.filter(F.col("fraud") | ((F.col("channel") == "human_initiated") & (F.rand(seed + 14) < 0.003)))
disp = disp.withColumn("dp", F.concat(F.lit("dp_"), F.substring(F.sha2(F.col("ch"), 256), 1, 24)))
disp = disp.withColumn("reason", F.when(F.col("fraud"), "fraudulent").otherwise("product_not_received"))
events = events.unionByName(mk(disp, "charge.dispute.created", F.col("t0") + F.expr("interval 5 days"), "dp", F.col("dp"),
                               common() + [F.col("ch").alias("charge"), F.col("reason").alias("reason")]))

# 1) at-least-once delivery: re-deliver ~3% of events with a later ingested_at
dups = events.sample(0.03, seed).withColumn("ingested_at", F.col("ingested_at") + F.expr("interval 7 minutes"))
events = events.unionByName(dups)

out = (events.withColumn("_source_file", F.lit(f"synthetic:gen_stripe_events:{ds}"))
       .withColumn("_origin", F.lit("synthetic"))
       .withColumn("ds", F.lit(ds)))
out.write.mode("overwrite").partitionBy("ds").parquet(f"{lake}/bronze/stripe_events_raw")
print(f"BRONZE stripe_events_raw ds={ds}: {out.count()} events")
spark.stop()
