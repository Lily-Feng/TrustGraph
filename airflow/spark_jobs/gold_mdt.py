"""Silver -> Gold: 8-dimension Merchant Digital Twin scores + supporting tables. Usage: gold_mdt.py <lake>

All dimension scores are in [0,1], higher = more trustworthy, and are Bayesian-smoothed toward
the marketplace average so sellers with few orders are not over- or under-rewarded.
Some dimensions are PROXIES (Olist has no explicit comms/resolution data) -- see DIMENSIONS.
"""
import sys

from pyspark.sql import functions as F

from _common import session

lake = sys.argv[1]
MIN_ORDERS = 20      # sellers below this are kept but flagged not eligible
SMOOTH_M = 10        # pseudo-observations pulled toward the prior
spark = session("gold_mdt")
S = lambda n: spark.read.parquet(f"{lake}/silver/{n}")


def write(df, name):
    df.write.mode("overwrite").parquet(f"{lake}/gold/{name}")
    print(f"GOLD {name}: {df.count()} rows")


clip01 = lambda c: F.greatest(F.lit(0.0), F.least(F.lit(1.0), c))

orders, items = S("olist_orders"), S("olist_order_items")
reviews = S("olist_reviews").groupBy("order_id").agg(F.min("score").alias("score"))
prod = S("olist_products")

# price relative to the category median (item level), averaged per order-seller
items = items.join(prod, "product_id", "left")
med = items.groupBy("category").agg(F.percentile_approx("price_brl", 0.5).alias("cat_median"))
items = items.join(med, "category", "left").withColumn("price_ratio", F.col("price_brl") / F.col("cat_median"))

# fx: monthly BRL per USD for converting ticket sizes (Olist period)
brl = (S("fx_rates").filter(F.col("currency") == "BRL")
       .groupBy(F.date_trunc("month", "date").alias("m")).agg(F.avg("rate").alias("brl_per_usd")))
fallback_rate = brl.agg(F.avg("brl_per_usd")).first()[0] or 3.5

os_ = (items.groupBy("order_id", "seller_id").agg(
          F.sum("price_brl").alias("order_value_brl"), F.avg("price_ratio").alias("price_ratio"),
          F.max("ship_by").alias("ship_by"))
       .join(orders, "order_id").join(reviews, "order_id", "left")
       .withColumn("m", F.date_trunc("month", "purchased_at"))
       .join(brl, "m", "left")
       .withColumn("order_value_usd", F.col("order_value_brl") / F.coalesce("brl_per_usd", F.lit(fallback_rate))))

delivered = F.col("delivered_at").isNotNull() & (F.col("order_status") == "delivered")
os_ = (os_
       .withColumn("is_delivered", delivered.cast("int"))
       .withColumn("delay_days", F.when(delivered, F.datediff("delivered_at", "estimated_at")))
       .withColumn("on_time", F.when(delivered, (F.col("delay_days") <= 0).cast("int")))
       .withColumn("late_days", F.when(delivered, F.greatest(F.col("delay_days"), F.lit(0))))
       .withColumn("handoff_days", (F.col("carrier_at").cast("long") - F.col("approved_at").cast("long")) / 86400)
       .withColumn("handoff_ok", F.when(F.col("carrier_at").isNotNull() & F.col("ship_by").isNotNull(),
                                        (F.col("carrier_at") <= F.col("ship_by")).cast("int")))
       .withColumn("bad", (F.col("order_status").isin("canceled", "unavailable") | (F.col("score") <= 2)).cast("int"))
       .withColumn("late", F.when(delivered, (F.col("delay_days") > 0).cast("int")))
       .withColumn("late_and_happy", F.when(F.col("late") == 1, (F.col("score") >= 4).cast("int"))))

g = os_.groupBy("seller_id").agg(
    F.count("*").alias("n_orders"),
    F.sum("is_delivered").alias("n_delivered"),
    F.sum("on_time").alias("k_on_time"), F.count("on_time").alias("n_on_time"),
    F.sum("late_days").alias("s_late_days"),
    F.sum("handoff_days").alias("s_handoff"), F.count("handoff_days").alias("n_handoff"),
    F.sum("handoff_ok").alias("k_handoff_ok"), F.count("handoff_ok").alias("n_handoff_ok"),
    F.sum("bad").alias("k_bad"),
    F.sum("late").alias("n_late"), F.sum("late_and_happy").alias("k_late_happy"),
    F.avg("price_ratio").alias("avg_price_ratio"), F.stddev("delay_days").alias("sd_delay"),
    F.avg("order_value_usd").alias("avg_ticket_usd"), F.sum("order_value_usd").alias("gmv_usd"),
    F.avg("score").alias("avg_review"))

glob = g.agg(*[F.sum(c).alias(c) for c in
               ["n_orders", "k_on_time", "n_on_time", "s_late_days", "s_handoff", "n_handoff",
                "k_handoff_ok", "n_handoff_ok", "k_bad", "n_late", "k_late_happy"]]).first()
pr = lambda k, n: (glob[k] or 0) / max(glob[n] or 1, 1)
prior = dict(on_time=pr("k_on_time", "n_on_time"), late_days=pr("s_late_days", "n_on_time"),
             handoff=pr("s_handoff", "n_handoff"), handoff_ok=pr("k_handoff_ok", "n_handoff_ok"),
             bad=pr("k_bad", "n_orders"), happy=pr("k_late_happy", "n_late"))
print("PRIORS", prior)
sm = lambda k, n, p, m=SMOOTH_M: (F.coalesce(F.col(k), F.lit(0)) + m * p) / (F.coalesce(F.col(n), F.lit(0)) + m)

d = (g
     .withColumn("on_time_rate", sm("k_on_time", "n_on_time", prior["on_time"]))
     .withColumn("mean_late_days", sm("s_late_days", "n_on_time", prior["late_days"]))
     .withColumn("mean_handoff_days", sm("s_handoff", "n_handoff", prior["handoff"]))
     .withColumn("handoff_ok_rate", sm("k_handoff_ok", "n_handoff_ok", prior["handoff_ok"]))
     .withColumn("bad_rate", sm("k_bad", "n_orders", prior["bad"]))
     .withColumn("recovery_rate", sm("k_late_happy", "n_late", prior["happy"], 5))
     .withColumn("delivery", clip01(F.col("on_time_rate")))
     .withColumn("price", clip01(F.lit(1.5) - F.coalesce("avg_price_ratio", F.lit(1.0))))
     .withColumn("contract", clip01(1 - F.col("mean_late_days") / 7))
     .withColumn("latency", clip01(1 - F.col("mean_handoff_days") / 7))
     .withColumn("dispute", clip01(1 - F.col("bad_rate") / 0.3))
     .withColumn("consistency", clip01(1 - F.coalesce("sd_delay", F.lit(10.0)) / 15))
     .withColumn("comms", clip01(F.col("handoff_ok_rate")))
     .withColumn("resolution", clip01(F.col("recovery_rate"))))

DIMS = ["delivery", "price", "contract", "latency", "dispute", "consistency", "comms", "resolution"]
WEIGHTS = {k: 1 / 8 for k in DIMS}
d = d.withColumn("mdt_score", sum(F.col(k) * w for k, w in WEIGHTS.items())) \
     .withColumn("eligible", F.col("n_orders") >= MIN_ORDERS) \
     .withColumn("tier", F.when(F.col("mdt_score") >= 0.75, "trusted").when(F.col("mdt_score") >= 0.60, "watch").otherwise("risk"))

sellers = S("olist_sellers")
merchants = (d.join(sellers, "seller_id", "left")
             .withColumn("merchant_id", F.col("seller_id"))
             .withColumn("account_id", F.concat(F.lit("acct_"), F.substring("seller_id", 1, 16)))
             .withColumn("merchant_name", F.concat(F.lit("Seller "), F.substring("seller_id", 1, 5), F.lit(" · "),
                                                  F.initcap("city"), F.lit(", "), F.upper("state")))
             .select("merchant_id", "account_id", "merchant_name", "city", "state", "n_orders", "eligible",
                     "mdt_score", "tier", *DIMS, "avg_review", "avg_ticket_usd", "gmv_usd",
                     "on_time_rate", "mean_late_days", "mean_handoff_days", "handoff_ok_rate",
                     "bad_rate", "recovery_rate", "avg_price_ratio", "sd_delay"))
write(merchants, "merchant_dimension_scores")

# ---------------- agentic payment risk (synthetic Stripe-shaped events) ----------------
ev = S("stripe_events")
rate = S("fx_rates")
last = (rate.withColumn("rn", F.row_number().over(__import__("pyspark.sql.window", fromlist=["Window"]).Window.partitionBy("currency").orderBy(F.col("date").desc())))
        .filter("rn = 1").select("currency", F.col("rate").alias("per_usd")))
usd_rows = [("usd", 1.0)]
last = last.unionByName(spark.createDataFrame(usd_rows, ["currency", "per_usd"]))
ev = ev.join(F.broadcast(last), "currency", "left").withColumn("amount_usd", F.col("amount") / F.col("per_usd"))

pay = ev.filter(F.col("event_type") == "payment_intent.created")
okp = ev.filter(F.col("event_type") == "payment_intent.succeeded")
canc = ev.filter(F.col("event_type") == "payment_intent.canceled")
disp = ev.filter(F.col("event_type") == "charge.dispute.created")

by_acct = (pay.groupBy("account_id").agg(
              F.count("*").alias("payments"), F.sum("amount_usd").alias("volume_usd"),
              F.avg((F.col("initiation_channel") != "human_initiated").cast("int")).alias("agent_share"),
              F.sum(F.col("mandate_violation").cast("int")).alias("mandate_violations"))
           .join(disp.groupBy("account_id").agg(F.count("*").alias("disputes")), "account_id", "left")
           .na.fill({"disputes": 0})
           .withColumn("dispute_rate", F.col("disputes") / F.col("payments"))
           .withColumn("mandate_violation_rate", F.col("mandate_violations") / F.col("payments")))
write(by_acct, "merchant_payment_risk")

chan = (pay.groupBy("initiation_channel").agg(F.count("*").alias("payments"),
                                              F.avg("amount_usd").alias("avg_amount_usd"),
                                              F.sum("amount_usd").alias("volume_usd"))
        .join(disp.groupBy("initiation_channel").agg(F.count("*").alias("disputes")), "initiation_channel", "left")
        .join(canc.groupBy("initiation_channel").agg(F.count("*").alias("canceled")), "initiation_channel", "left")
        .na.fill(0).withColumn("dispute_rate", F.col("disputes") / F.col("payments"))
        .withColumn("cancel_rate", F.col("canceled") / F.col("payments")))
write(chan, "channel_risk")

# ---------------- external dispute/resolution benchmarks (real CFPB complaints) ----------------
c = S("cfpb_complaints")
relief = F.col("company_response").isin("Closed with monetary relief", "Closed with non-monetary relief")
bench = (c.groupBy("product").agg(
            F.count("*").alias("complaints"), F.avg(F.col("timely").cast("int")).alias("timely_response_rate"),
            F.avg(relief.cast("int")).alias("relief_rate"),
            F.avg((F.col("company_response") == "Closed with explanation").cast("int")).alias("explanation_only_rate"))
         .orderBy(F.desc("complaints")))
write(bench, "external_dispute_benchmarks")
spark.stop()
