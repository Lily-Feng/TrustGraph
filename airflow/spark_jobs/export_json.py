"""Gold -> data/merchant_scores.json for the static TrustGraph demo. Usage: export_json.py <lake> <export_dir>"""
import json
import os
import sys
from datetime import datetime, timezone

from pyspark.sql import functions as F

from _common import session

lake, out_dir = sys.argv[1], sys.argv[2]
spark = session("export_json")
G = lambda n: spark.read.parquet(f"{lake}/gold/{n}")
rows = lambda df: [r.asDict(recursive=True) for r in df.collect()]
r4 = lambda v: round(v, 4) if isinstance(v, float) else v
clean = lambda rs: [{k: r4(v) for k, v in r.items()} for r in rs]

DIMS = ["delivery", "price", "contract", "latency", "dispute", "consistency", "comms", "resolution"]
pay = G("merchant_payment_risk").select("account_id", "payments", "volume_usd", "agent_share", "dispute_rate",
                                        "mandate_violation_rate")
m = (G("merchant_dimension_scores").filter("eligible")
     .join(pay, "account_id", "left").orderBy(F.desc("mdt_score")).limit(200))
merchants = []
for r in clean(rows(m)):
    merchants.append(dict(
        merchant_id=r["merchant_id"], name=r["merchant_name"], state=r["state"], orders=r["n_orders"],
        mdt_score=r["mdt_score"], tier=r["tier"], dimensions={k: r[k] for k in DIMS},
        avg_review=r["avg_review"], avg_ticket_usd=r["avg_ticket_usd"],
        payment_risk=None if r["payments"] is None else dict(
            payments=r["payments"], volume_usd=r["volume_usd"], agent_share=r["agent_share"],
            dispute_rate=r["dispute_rate"], mandate_violation_rate=r["mandate_violation_rate"])))

tiers = {r["tier"]: r["count"] for r in rows(G("merchant_dimension_scores").filter("eligible").groupBy("tier").count())}
doc = dict(
    meta=dict(
        generated_at=datetime.now(timezone.utc).isoformat(),
        sources=[
            dict(name="Olist Brazilian E-Commerce", kind="real", note="Public marketplace data 2016-2018; merchant dimensions are computed from it. Sellers are anonymised."),
            dict(name="CFPB Consumer Complaints", kind="real", note="Daily incremental feed; used only as an external dispute/resolution benchmark, not joined to merchants."),
            dict(name="Frankfurter FX (ECB)", kind="real", note="BRL->USD conversion of ticket sizes."),
            dict(name="Stripe-shaped agent payment events", kind="synthetic", note="Generated to spec/data-contract.md; payment_risk fields are synthetic."),
        ],
        dimensions={
            "delivery": "Share of delivered orders arriving on or before the promised date.",
            "price": "Item price vs category median (cheaper = higher).",
            "contract": "Severity of broken delivery promises (mean days late).",
            "latency": "Days from payment approval to carrier handoff.",
            "dispute": "Share of orders cancelled/unavailable or rated <=2 stars (inverted).",
            "consistency": "Spread of delivery delay (lower variance = higher).",
            "comms": "PROXY: share of orders handed to carrier before the seller's own ship-by date.",
            "resolution": "PROXY: share of late orders that still ended with a >=4 star review.",
        },
        scoring="Each dimension in [0,1], Bayesian-smoothed toward marketplace mean (m=10); mdt_score = equal-weight mean.",
        eligible_min_orders=20, tier_counts=tiers),
    merchants=merchants,
    channel_risk=clean(rows(G("channel_risk"))),
    cfpb_benchmarks=clean(rows(G("external_dispute_benchmarks").limit(15))))
os.makedirs(out_dir, exist_ok=True)
with open(f"{out_dir}/merchant_scores.json", "w") as f:
    json.dump(doc, f, indent=1, default=str)
print(f"EXPORT merchant_scores.json: {len(merchants)} merchants")
spark.stop()
