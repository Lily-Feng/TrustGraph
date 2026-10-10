"""Data-quality gates. Usage: dq_check.py <lake> <layer: bronze|silver|gold>

Exits non-zero (failing the Airflow task) if any check fails. Report -> gold/_dq/<layer>.json
"""
import json
import os
import sys
from datetime import datetime, timezone

from pyspark.sql import functions as F

from _common import session

lake, layer = sys.argv[1], sys.argv[2]
spark = session(f"dq_{layer}")

# table -> {min_rows, not_null:[...], unique:[...], between:{col:(lo,hi)}}
CHECKS = {
    "bronze": {
        "olist/orders": dict(min_rows=90000, not_null=["order_id"]),
        "olist/order_items": dict(min_rows=100000, not_null=["order_id", "seller_id"]),
        "olist/sellers": dict(min_rows=3000, unique=["seller_id"]),
        "cfpb_complaints": dict(min_rows=1000, not_null=["complaint_id"]),
        "fx_rates": dict(min_rows=100, not_null=["date", "currency", "rate"]),
        "stripe_events_raw": dict(min_rows=10000, not_null=["event_id", "payload"]),
    },
    "silver": {
        "olist_orders": dict(min_rows=90000, unique=["order_id"]),
        "olist_reviews": dict(min_rows=90000, between={"score": (1, 5)}),
        "cfpb_complaints": dict(min_rows=1000, unique=["complaint_id"], not_null=["company", "received_on"]),
        "fx_rates": dict(min_rows=100, unique=["date", "currency"], between={"rate": (0.0001, 100000)}),
        "stripe_events": dict(min_rows=10000, unique=["event_id"], not_null=["account_id", "amount"],
                              between={"amount": (0, 1e7)}),
    },
    "gold": {
        "merchant_dimension_scores": dict(min_rows=2000, unique=["merchant_id"], not_null=["mdt_score"],
                                          between={k: (0, 1) for k in
                                                   ["mdt_score", "delivery", "price", "contract", "latency",
                                                    "dispute", "consistency", "comms", "resolution"]}),
        "merchant_payment_risk": dict(min_rows=100, unique=["account_id"],
                                      between={"dispute_rate": (0, 1), "mandate_violation_rate": (0, 1)}),
        "channel_risk": dict(min_rows=3),
        "external_dispute_benchmarks": dict(min_rows=3, between={"timely_response_rate": (0, 1)}),
    },
}

results, failed = [], False


def record(table, check, ok, detail=""):
    global failed
    failed |= not ok
    results.append(dict(table=table, check=check, ok=bool(ok), detail=str(detail)))
    print(("PASS " if ok else "FAIL ") + f"{layer}.{table} {check} {detail}")


for table, spec in CHECKS[layer].items():
    path = f"{lake}/{layer}/{table}"
    if not os.path.exists(path):
        record(table, "exists", False, path)
        continue
    df = spark.read.parquet(path)
    n = df.count()
    record(table, "min_rows", n >= spec.get("min_rows", 1), f"{n} >= {spec.get('min_rows', 1)}")
    for col in spec.get("not_null", []):
        bad = df.filter(F.col(col).isNull()).count()
        record(table, f"not_null[{col}]", bad == 0, f"{bad} nulls")
    if spec.get("unique"):
        dup = n - df.select(*spec["unique"]).distinct().count()
        record(table, f"unique{spec['unique']}", dup == 0, f"{dup} duplicates")
    for col, (lo, hi) in spec.get("between", {}).items():
        bad = df.filter(F.col(col).isNotNull() & ((F.col(col) < lo) | (F.col(col) > hi))).count()
        record(table, f"range[{col}]", bad == 0, f"{bad} outside [{lo},{hi}]")

os.makedirs(f"{lake}/gold/_dq", exist_ok=True)
with open(f"{lake}/gold/_dq/{layer}.json", "w") as f:
    json.dump(dict(layer=layer, run_at=datetime.now(timezone.utc).isoformat(),
                   passed=not failed, results=results), f, indent=1)
spark.stop()
if failed:
    sys.exit("DQ gate failed: " + layer)
