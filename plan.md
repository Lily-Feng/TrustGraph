# TrustGraph — 1-Week Implementation Plan

## Project Goal

Build a Databricks-based **real-time fraud detection + merchant trust platform** that combines:

- Transaction fraud scoring
- Merchant trust scoring
- Streaming / velocity features
- Customer–merchant–device–IP–bank relationship graphs
- Fraud-ring detection
- Delayed fraud / chargeback labels
- MLflow model tracking
- Feature Store / online feature lookup
- Model Serving
- Risk analytics dashboard
- Optional AI fraud-investigator assistant

The goal for this week is **not** to build a production payment network. The goal is to create a convincing end-to-end prototype that demonstrates the architecture and product idea.

---

# 1. Target Architecture

```text
Synthetic Data Generator
        |
        |-- Customers
        |-- Merchants
        |-- Devices
        |-- Payment Methods
        |-- IP Addresses
        |-- Bank Accounts
        |
        |-- Transactions
        |-- Fraud Rings
        |-- Chargebacks
        |-- Merchant Events
        v
+--------------------------+
| Databricks Bronze Layer  |
+--------------------------+
              |
              v
+--------------------------+
| Silver / Cleaned Data    |
| Lakeflow Pipelines       |
+--------------------------+
              |
       +------+------+
       |             |
       v             v
Streaming       Graph / Batch
Features         Features
       |             |
       +------+------+
              v
        Feature Tables
              |
       +------+------+
       |             |
       v             v
Transaction      Merchant
Fraud Model      Trust Model
       |             |
       +------+------+
              v
       Decision Engine
              |
       +------+------+ 
       |      |      |
    APPROVE REVIEW DECLINE
              |
              v
      Risk Operations UI
```

---

# 2. MVP Scope

## Must Have

By the end of the week, the project should support:

1. Synthetic customers, merchants, devices, IPs, payment methods, and bank accounts.
2. At least **1–5 million synthetic transactions** for development/demo.
3. Multiple intentional fraud patterns.
4. Merchant-level trust features.
5. Streaming or simulated streaming transaction ingestion.
6. Transaction fraud model.
7. Merchant trust score.
8. Network-risk features.
9. A unified transaction decision score.
10. Dashboard showing fraud and merchant risk.
11. One investigation workflow showing *why* a transaction or merchant is risky.

## Stretch Goals

Only do these after the MVP works:

- 20M+ transactions
- Databricks Online Feature Store
- Real-time Model Serving
- Graph visualization UI
- Genie
- AI fraud investigator agent
- Databricks App
- Automated retraining workflow

---

# 3. Core Data Model

## customers

```text
customer_id
created_at
country
city
risk_segment
verification_level
home_lat
home_long
```

## merchants

```text
merchant_id
created_at
merchant_category
country
city
verification_status
owner_id
bank_account_id
baseline_daily_volume
baseline_avg_ticket
merchant_persona
```

Possible merchant personas:

```text
normal
new
high_growth
struggling
malicious
```

## devices

```text
device_id
device_type
os
first_seen
```

## ip_addresses

```text
ip_id
country
region
risk_type
```

## payment_methods

```text
payment_method_id
customer_id
payment_type
created_at
```

## bank_accounts

```text
bank_account_id
created_at
country
bank_name
```

## transactions

```text
transaction_id
event_time

customer_id
merchant_id
device_id
ip_id
payment_method_id

amount
currency
channel

status

fraud_scenario
is_fraud
```

## chargebacks

```text
chargeback_id
transaction_id
reported_at
reason
is_confirmed_fraud
```

## merchant_events

```text
merchant_id
event_time
event_type

bank_change
owner_change
address_change
verification_change
```

---

# 4. Fraud Scenarios

Do not assign fraud randomly.

Generate fraud through behavioral scenarios.

## Scenario A — Account Takeover

Pattern:

```text
existing customer
+
new device
+
new IP / location
+
high-value transaction
+
unusual merchant
```

Features created:

```text
new_device
distance_from_previous_txn
amount_vs_customer_avg
new_country
```

---

## Scenario B — Card Testing

Pattern:

```text
same payment method
+
many small transactions
+
many merchants
+
short time window
```

Features:

```text
payment_txn_count_1m
payment_unique_merchants_5m
small_payment_velocity
```

---

## Scenario C — Fraud Ring

Create groups such as:

```text
20 customers
3 devices
2 IP addresses
4 merchants
```

The entities intentionally share infrastructure.

Graph features:

```text
shared_device_count
shared_ip_count
risky_neighbor_ratio
connected_component_size
distance_to_confirmed_fraud
```

---

## Scenario D — Merchant Collusion

Pattern:

```text
multiple merchants
sharing:
- bank account
- owner
- devices
- customer clusters
```

Add elevated chargeback rates.

---

## Scenario E — Bust-Out Merchant

Timeline:

```text
Month 1–3
normal behavior

Month 4
rapid growth

Month 5
average ticket increases

Month 6
risky customers increase

Month 7
chargebacks spike
```

Expected Merchant Trust:

```text
92 -> 88 -> 74 -> 51 -> 24
```

---

# 5. Merchant Trust Score

Use a 0–100 score.

```text
0 = extremely risky
100 = highly trusted
```

Build the score from multiple dimensions.

## Identity Risk

Examples:

```text
merchant_age_days
business_verified
owner_verified
bank_account_age
recent_bank_change
```

## Transaction Risk

```text
fraud_rate_7d
fraud_rate_30d
chargeback_rate_30d
refund_rate
decline_rate
volume_growth
avg_ticket_change
```

## Customer Quality

```text
risky_customer_ratio
new_customer_ratio
repeat_customer_rate
avg_customer_risk
```

## Behavioral Risk

```text
volume_zscore
avg_ticket_zscore
new_customer_spike
country_distribution_shift
```

## Network Risk

```text
shared_bank_bad_merchants
shared_owner_bad_merchants
shared_device_bad_merchants
risky_neighbor_ratio
distance_to_bad_merchant
```

Initial MVP formula:

```text
merchant_risk =
    0.30 * transaction_risk
  + 0.20 * identity_risk
  + 0.20 * behavioral_risk
  + 0.15 * customer_risk
  + 0.15 * network_risk

merchant_trust_score =
    100 * (1 - merchant_risk)
```

Later, replace some weighted components with ML.

---

# 6. Transaction Fraud Features

## Transaction Features

```text
amount
channel
merchant_category
transaction_hour
```

## Customer Features

```text
customer_txn_count_5m
customer_txn_count_1h

customer_amount_1h

customer_avg_amount_30d

amount_vs_customer_avg

days_since_last_transaction
```

## Device Features

```text
device_txn_count_5m
device_unique_customers_1h
device_unique_payment_methods_1h
```

## IP Features

```text
ip_txn_count_5m
ip_unique_customers_1h
ip_unique_devices_1h
```

## Merchant Features

```text
merchant_txn_count_5m
merchant_volume_10m
merchant_avg_ticket_30d
merchant_trust_score
```

## Network Features

```text
customer_bad_neighbor_ratio
merchant_bad_neighbor_ratio
shared_device_risk
shared_ip_risk
```

---

# 7. Unified Risk Decision

Example MVP formula:

```text
final_risk =
    0.60 * transaction_fraud_probability
  + 0.25 * merchant_risk
  + 0.15 * network_risk
```

Example policy:

```text
risk < 0.35
APPROVE

0.35 <= risk < 0.70
REVIEW

risk >= 0.70
DECLINE
```

These thresholds are demo settings, not production recommendations.

---

# 8. Databricks Layout

Suggested catalog:

```text
trustgraph_dev
```

Schemas:

```text
trustgraph_dev.bronze
trustgraph_dev.silver
trustgraph_dev.features
trustgraph_dev.analytics
trustgraph_dev.ml
```

Example tables:

```text
trustgraph_dev.bronze.transactions_raw

trustgraph_dev.silver.transactions
trustgraph_dev.silver.customers
trustgraph_dev.silver.merchants

trustgraph_dev.features.customer_features
trustgraph_dev.features.merchant_features
trustgraph_dev.features.device_features
trustgraph_dev.features.network_features

trustgraph_dev.analytics.risk_decisions
trustgraph_dev.analytics.merchant_trust_daily
```

---

# 9. Repository Structure

```text
trustgraph/
|
|-- README.md
|-- plan.md
|
|-- config/
|   |-- simulation.yaml
|
|-- notebooks/
|   |-- 01_generate_entities.py
|   |-- 02_generate_transactions.py
|   |-- 03_generate_fraud_scenarios.py
|   |-- 04_bronze_ingestion.py
|   |-- 05_silver_pipeline.py
|   |-- 06_streaming_features.py
|   |-- 07_graph_features.py
|   |-- 08_merchant_trust.py
|   |-- 09_train_fraud_model.py
|   |-- 10_score_transactions.py
|   |-- 11_dashboard_queries.sql
|
|-- src/
|   |-- simulation/
|   |-- features/
|   |-- models/
|   |-- scoring/
|
|-- tests/
|
|-- dashboards/
|
|-- docs/
|   |-- architecture.md
|   |-- fraud-scenarios.md
```

---

# 10. Simulation Configuration

Create:

```text
config/simulation.yaml
```

Example:

```yaml
seed: 42

customers: 100000
merchants: 10000
devices: 200000
payment_methods: 150000
ip_addresses: 50000

transactions: 5000000

fraud:
  base_rate: 0.004

  account_takeover:
    enabled: true
    count: 2000

  card_testing:
    enabled: true
    count: 1000

  fraud_rings:
    enabled: true
    ring_count: 100

  malicious_merchants:
    enabled: true
    count: 200

chargeback:
  min_delay_days: 7
  max_delay_days: 45
```

This makes the simulation reproducible and scalable.

---

# 11. One-Week Implementation Schedule

# Day 1 — Build the Synthetic World

## Goal

Finish the base entity model and generate believable normal transactions.

## Tasks

### Morning

Define schemas for:

```text
customers
merchants
devices
payment_methods
ip_addresses
bank_accounts
```

Create simulation configuration.

Generate:

```text
100K customers
10K merchants
200K devices
150K payment methods
50K IPs
```

### Afternoon

Build normal transaction generator.

Generate approximately:

```text
1M transactions
```

Make distributions realistic.

Use:

```text
log-normal
Poisson
Zipf / long-tail behavior
```

Examples:

- Transaction amount = log-normal.
- Merchant popularity = long-tail.
- Customer activity = uneven.
- Transaction hour = time-of-day distribution.

### Deliverable

Working Delta tables for:

```text
customers
merchants
devices
payment_methods
ip_addresses
transactions
```

### Definition of Done

You can run:

```sql
SELECT merchant_id, COUNT(*)
FROM transactions
GROUP BY merchant_id;
```

and see a realistic long-tail distribution.

---

# Day 2 — Inject Fraud and Build the Graph

## Goal

Create meaningful fraud scenarios and entity relationships.

## Tasks

Implement:

```text
Account Takeover
Card Testing
Fraud Rings
Merchant Collusion
Bust-Out Merchants
```

Create edge tables:

```text
customer_device_edges
customer_ip_edges
customer_merchant_edges
merchant_bank_edges
merchant_owner_edges
```

Generate delayed chargebacks.

Example:

```text
transaction
  -> 7–45 days
  -> chargeback
  -> confirmed fraud
```

### Deliverable

At least:

```text
1M+ transactions
50+ fraud rings
100+ malicious merchants
```

### Definition of Done

You can identify a fraud ring using graph relationships without looking directly at the `is_fraud` column.

---

# Day 3 — Databricks Bronze / Silver / Streaming Pipeline

## Goal

Turn the synthetic world into a real data-engineering pipeline.

## Tasks

Create Bronze ingestion.

Bronze tables:

```text
transactions_raw
customers_raw
merchants_raw
chargebacks_raw
merchant_events_raw
```

Create Silver tables.

Perform:

```text
deduplication
schema validation
null handling
timestamp normalization
quality checks
```

Add expectations such as:

```text
transaction_id IS NOT NULL
amount > 0
customer_id IS NOT NULL
merchant_id IS NOT NULL
```

Simulate transaction streaming.

Possible MVP approach:

```text
transaction files
    ->
Auto Loader / streaming ingestion
    ->
bronze.transactions_raw
```

### Deliverable

Working incremental pipeline:

```text
Synthetic Generator
    ->
Bronze
    ->
Silver
```

### Definition of Done

New transaction files automatically appear in the Silver transaction table.

---

# Day 4 — Feature Engineering + Merchant Trust

## Goal

Produce the feature layer that makes the project interesting.

## Tasks

Build windowed features.

Examples:

```text
customer_txn_count_5m
customer_amount_1h

device_unique_customers_1h

ip_unique_customers_1h

merchant_volume_10m
merchant_txn_count_5m
```

Build merchant historical features:

```text
fraud_rate_30d
chargeback_rate_30d
avg_ticket_30d
volume_growth_7d
repeat_customer_rate
```

Build network features:

```text
shared_device_count
shared_bank_count
risky_neighbor_ratio
connected_component_size
```

Create:

```text
merchant_trust_score
```

Persist daily snapshots:

```text
merchant_id
date
trust_score
identity_risk
transaction_risk
behavioral_risk
customer_risk
network_risk
```

### Deliverable

```text
features.customer_features
features.device_features
features.merchant_features
features.network_features
analytics.merchant_trust_daily
```

### Definition of Done

You can show one merchant whose trust score declines over time because of simulated suspicious behavior.

---

# Day 5 — Train Fraud Model

## Goal

Train a transaction fraud model and connect it to merchant trust.

## Tasks

Build a training dataset.

Important:

Use historical features only.

Avoid label leakage.

Use delayed fraud labels.

Train:

```text
Logistic Regression baseline
XGBoost / LightGBM main model
```

Track experiments with MLflow.

Metrics:

```text
PR-AUC
Precision
Recall
False Positive Rate
Fraud Dollars Captured
```

Do NOT make accuracy the primary metric.

Compare models.

Register the winner.

### Deliverable

MLflow experiment with:

```text
baseline model
tree model
metrics
feature importance
registered model
```

### Definition of Done

The model scores unseen transactions and merchant trust is included as a feature.

---

# Day 6 — Decision Engine + Dashboard

## Goal

Turn ML results into a visible risk product.

## Tasks

Calculate:

```text
transaction_fraud_probability
merchant_risk
network_risk
final_risk
```

Produce:

```text
APPROVE
REVIEW
DECLINE
```

Create risk decision table.

Build Databricks SQL / AI/BI Dashboard.

## Dashboard Page 1 — Risk Operations

KPIs:

```text
Transactions Today

Fraud Rate

Fraud Dollars Blocked

High-Risk Merchants

Review Queue
```

Charts:

```text
Fraud rate over time

Merchant trust distribution

Fraud by merchant category

Decision distribution
```

## Dashboard Page 2 — Merchant Trust

Show:

```text
merchant trust score
risk components
trust score timeline
transaction volume
chargeback rate
```

## Dashboard Page 3 — Investigation

Pick one suspicious transaction.

Show:

```text
Risk Score: 92

Merchant Trust: 28

Device Accounts: 19

Customer Velocity: 12 / 5 min

Amount vs Baseline: 8.4x
```

### Deliverable

A usable fraud-operations dashboard.

### Definition of Done

A reviewer can understand *why* a transaction or merchant is risky without opening a notebook.

---

# Day 7 — Production Polish + Demo Story

## Goal

Make the project portfolio-ready.

## Morning

Create a workflow:

```text
generate data
    ->
ingest
    ->
transform
    ->
compute features
    ->
score merchants
    ->
train / score fraud
    ->
refresh analytics
```

Use Lakeflow Jobs where practical.

Add:

```text
logging
configuration
basic tests
failure handling
```

## Afternoon

Create the final demo story.

Demo sequence:

### Step 1

Show a normal merchant.

```text
Trust Score: 91
```

### Step 2

Simulate suspicious merchant activity.

```text
volume +420%
new customers +300%
chargebacks increasing
shared bank account detected
```

### Step 3

Show merchant trust falling.

```text
91 -> 76 -> 53 -> 27
```

### Step 4

Stream a suspicious transaction.

Show:

```text
Transaction Fraud Probability: 0.68
Merchant Risk: 0.73
Network Risk: 0.81
```

### Step 5

Decision engine returns:

```text
FINAL RISK = 0.72

DECISION = DECLINE
```

### Step 6

Show investigation explanation.

Example:

```text
Primary risk drivers:

1. Merchant trust score declined to 27.
2. Device was used by 14 customer accounts.
3. Merchant shares a bank account with a previously flagged merchant.
4. Transaction amount is 7.9x above customer baseline.
5. Customer performed 11 transactions in five minutes.
```

---

# 12. Optional Day-7 Stretch: Fraud Investigator Copilot

Only build this if everything else works.

Input:

```text
Investigate merchant M1847.
```

The assistant retrieves:

```text
merchant features
merchant trust history
transaction anomalies
network relationships
fraud decisions
chargeback history
```

Output:

```text
Merchant M1847 is high risk because transaction volume increased
430% in 72 hours, chargeback rate rose from 0.8% to 6.2%, and its
settlement account is shared with two high-risk merchants.
```

The assistant should summarize evidence.

The human analyst remains responsible for the final decision.

---

# 13. Daily Time Priorities

If time becomes limited, prioritize in this order:

```text
1. Synthetic data
2. Fraud scenarios
3. Merchant trust features
4. Fraud model
5. Risk decision engine
6. Dashboard
7. Streaming
8. Graph features
9. Model Serving
10. AI assistant
```

Do not sacrifice the core product to add flashy AI features.

---

# 14. Scaling Strategy

Development:

```text
100K customers
10K merchants
1–5M transactions
```

Demo / benchmark:

```text
500K customers
25K merchants
20M transactions
```

Large-scale test:

```text
1M+ customers
50K+ merchants
100M+ transactions
```

Only scale after the logic works.

---

# 15. What Not to Do This Week

Avoid:

- Building a custom graph database.
- Building a full frontend before the data pipeline works.
- Training deep-learning models.
- Generating 1B random transactions.
- Spending two days optimizing model accuracy.
- Building RAG just because it uses GenAI.
- Over-engineering microservices.
- Adding 30 fraud scenarios.

A clean implementation of five fraud scenarios is much stronger than 30 incomplete ones.

---

# 16. Final Demo Requirements

By the end of Day 7, you should be able to demonstrate this entire story in under 10 minutes:

```text
1. Synthetic financial ecosystem exists.

2. Transactions arrive continuously.

3. Databricks computes real-time / recent behavior features.

4. Merchant trust changes as behavior changes.

5. Graph relationships identify suspicious entity networks.

6. Fraud ML scores transactions.

7. Merchant risk influences transaction decisions.

8. Risk engine approves, reviews, or declines transactions.

9. Dashboard shows fraud operations.

10. Analyst can understand why a decision was made.
```

---

# 17. Portfolio Description

## Project Title

**TrustGraph — Real-Time Fraud & Merchant Trust Intelligence Platform**

## One-Line Description

Built a network-aware risk platform on Databricks combining streaming transaction fraud detection, merchant trust scoring, behavioral features, graph-based entity risk, MLflow model management, and fraud investigation analytics.

## Resume Bullets

- Built a Databricks fraud-risk platform processing synthetic transaction streams across customers, merchants, devices, IP addresses, payment instruments, and settlement accounts.
- Developed merchant trust scoring using transaction quality, behavioral anomalies, customer risk, verification signals, and graph-network relationships.
- Engineered windowed velocity and network-risk features for fraud detection and trained transaction-risk models tracked with MLflow.
- Created a unified decision engine combining transaction, merchant, and network risk into APPROVE / REVIEW / DECLINE outcomes.
- Designed fraud-operations analytics for merchant trust trends, suspicious network relationships, fraud-dollar capture, and case investigation.

---

# 18. Success Criteria

The project is successful if:

- Fraud labels come from intentional behavioral scenarios rather than random assignment.
- Merchant trust changes dynamically over time.
- Graph relationships materially affect risk.
- The fraud model uses merchant trust as an input.
- Streaming or incremental features are part of the scoring pipeline.
- Risk decisions are explainable.
- The entire pipeline runs end to end.
- The demo tells one clear fraud story.

The key differentiator should remain:

> Traditional fraud systems score a transaction. TrustGraph scores the transaction, the merchant, and the network around them.
