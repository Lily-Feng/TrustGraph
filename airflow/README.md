# TrustGraph data pipeline (Airflow + Spark, local)

Feeds the Merchant Digital Twin (MDT) demo with an 8-dimension trust score per merchant.

```
make up        # Airflow http://localhost:8080 (admin/admin), Spark UI http://localhost:8082
make smoke     # sanity check
make pipeline  # Bronze -> Silver -> Gold -> ../data/merchant_scores.json
```
Needs Docker with >= 7 GB RAM. First `make pipeline` takes ~5 min (downloads ~60 MB).

## Layout
`dags/` Airflow DAGs · `spark_jobs/` PySpark · `include/` shared config + extract helpers ·
`lake/` Parquet medallion (gitignored) · output goes to `../data/merchant_scores.json`.
Airflow and the Spark master/worker run from the **same image**, so driver and executors share Python/PySpark versions.

## DAGs
| DAG | Schedule | What |
|---|---|---|
| `olist_bronze_ingest` | manual | Olist CSVs (public HF mirror, no login) + historic BRL/USD rates -> Bronze |
| `cfpb_complaints_incremental` | daily, 1 run = 1 `date_received` day | CFPB API via `search_after`, count-verified, idempotent partitions |
| `fx_rates_daily` | daily | Frankfurter rates -> Bronze |
| `stripe_events_synthetic` | daily | Synthetic Stripe-shaped webhook events (dupes, late arrival, API drift, JPY minor units) |
| `mdt_build_gold` | any upstream Bronze dataset updates | DQ(bronze) -> Silver -> DQ(silver) -> Gold -> DQ(gold) -> JSON export |

Daily DAGs are created paused; `make unpause` turns on scheduling.

## Data honesty
- **Real:** Olist (Brazilian marketplace 2016-18, anonymised sellers), CFPB complaints, ECB FX.
- **Synthetic:** the Stripe-style agent payment events (`_origin='synthetic'`). No public agent-payment data exists.
- Olist is a stand-in for merchant behaviour, not event-planning vendors. Two dimensions are **proxies**:
  `comms` (handoff before the seller's own ship-by date) and `resolution` (late orders that still got >=4 stars).
- CFPB is about financial firms, so it is an external dispute/resolution *benchmark*, not joined to merchants.
- Olist license: CC BY-NC-SA 4.0 (fine for a non-commercial demo).
