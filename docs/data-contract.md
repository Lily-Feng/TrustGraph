# Data Contract — Stripe-shaped, agent-aware

**Status: proposal.** This changes §3 (data model), §4 (scenarios), and Day 1–3 of `plan.md`.
Nothing here is committed to the plan yet.

---

## 0. Where this sits in the agentic payments stack

Using the eight-layer decomposition in `Agentic-payment.jpeg` as the frame:

| Layer | TrustGraph's relationship |
|---|---|
| 1 — Agent Communication & Discovery (A2A, MCP, agent cards) | **Out of scope.** Assumed upstream. |
| 2 — Agent Identity, Trust & Reputation (Visa TAP, ERC-8004, DID/VCs, reputation networks) | **Consumed as input, and partially built.** `agent.attestation_level` / `attestation_issuer` consume this layer; `agent_trust_score` *is* a reputation network — the diagram's own term for it. |
| 3 — Mandate, Consent & Policy (AP2, spending controls, audit & revocation) | **Consumed as input.** The `mandate` object below maps field-for-field onto "limits, categories, merchants, time windows, approvals"; `revoked_at` plus the decision audit trail covers "audit & revocation." |
| 4 — Offer, Quote & Transaction Coordination (ACP — OpenAI/Stripe, UCP) | **The data contract.** Stripe-shaped ingestion *is* this layer's output. |
| **5 — Payment Authentication, Risk & Compliance** (VIC, Mastercard Agent Pay, *fraud scoring, disputes, chargebacks*) | **This is TrustGraph.** The entire project lives in this box. |
| 6 — Machine-Speed Payment Protocols (x402, MPP, ATXP, paid MCP) | **Modeled as a channel, not implemented.** See the channel dimension in §5. |
| 7 — Settlement Rails | **Out of scope.** |
| 8 — Post-Transaction Lifecycle (disputes & chargebacks, refunds, reconciliation) | **Closes the label loop.** Disputes are where the delayed, noisy training label comes from. |

Three things follow from this.

**It gives you a one-sentence pitch that shows you see the whole board.** *"TrustGraph is a
Layer 5 risk implementation: it consumes Layer 2 attestations and Layer 3 mandates, scores Layer 4
transaction flow, and closes the loop with Layer 8 disputes."* Most candidates can describe their
own box. Naming the boxes on either side, and being explicit about which ones you deliberately did
not build, is the senior version of the same answer.

**It states your scope boundary out loud**, which is the same move your story inventory already
recommends for the eBay 2TB work — volunteering the boundary buys credibility for everything
inside it. You are not building settlement, discovery, or the protocols themselves.

**Two of these layers are Visa's.** Visa TAP sits at Layer 2 and Visa Intelligent Commerce at
Layer 5 — and TrustPulse, your original hackathon idea, was a Layer 2 trust attestation. Your
domain credibility here is specific and real, not a hobby interest. Say the layer numbers; they do
the work.

**Caveat:** this landscape moves fast and vendor maps go stale. The *layer decomposition* is sound
and stable; the specific protocol names under each layer should be re-verified before you cite them
in an interview. The data model below is deliberately built on the durable concepts — identity,
attestation, mandate, delegation, settlement — rather than on any one protocol's field names.

---

## 1. Why model on Stripe rather than invent a schema

Four reasons, in order of how much they matter for the portfolio:

1. **Bronze becomes real.** Generated tabular files make Bronze→Silver a rename. Stripe's actual
   delivery shape — nested JSON webhook envelopes, at-least-once delivery, out-of-order arrival,
   idempotency keys, integer minor units, API-version drift — makes Silver do genuine work:
   parsing, deduplication, late-arrival handling, schema quarantine, currency normalization. That
   is the data engineering story, and right now the plan doesn't have one.
2. **It is a real external data contract.** "Validate data contracts" and "API-based data ingestion
   from enterprise systems and third-party platforms" are stated requirements in JR2023258. Working
   to someone else's published schema demonstrates both; inventing your own demonstrates neither.
3. **Recognition.** An interviewer who has touched payments recognizes `pi_`, `ch_`, `dp_`,
   `evt_`, disputes, and Connect accounts immediately. Invented schemas cost you a minute of
   explanation and buy nothing.
4. **Free realism.** Stripe test mode is designed for exactly this and costs nothing.

## 2. Source strategy — captured contract, synthesized volume

Do not try to create 500K objects through the Stripe API; rate limits make that impractical and
pointless.

```text
Stripe test mode (real API)          src/simulation (synthetic)
        |                                     |
   ~200-500 real objects                 500K+ objects
   real webhook payloads                 conforming to captured schema
        |                                     |
        +----------------+--------------------+
                         v
              bronze.stripe_events_raw
```

**Phase 1 — capture (half day).** Hit Stripe test mode for real: create customers, payment
intents, charges (including the documented test cards that force declines and disputes), refunds,
and Connect accounts. Receive real webhooks. Persist raw envelopes untouched. Derive the schema and
the quirk inventory from what actually arrives, not from reading docs.

**Phase 2 — synthesize (Days 1–2).** The generator emits objects conforming to the captured
schema, at volume, with the behavioral fraud scenarios layered on.

**Phase 3 — mix.** Both land in the same Bronze table. The pipeline cannot tell them apart, which
is the point.

State this honestly in the writeup: *schema and edge cases captured from the live Stripe test-mode
API; volume synthesized to conform to that contract.* That sentence is more impressive than either
half alone.

**Hard rules:** test mode only, never live keys. Only Stripe's documented test card numbers. No
real cardholder data, no real PII, ever. `.env` for keys, gitignored, and the repo README says so.

## 3. Bronze — the envelope and the four quirks

Every row is one webhook event, stored raw:

```text
bronze.stripe_events_raw
  event_id            STRING     -- evt_...
  event_type          STRING     -- payment_intent.succeeded, charge.dispute.created, ...
  api_version         STRING     -- schema drift lives here
  created             TIMESTAMP  -- Stripe's event time
  ingested_at         TIMESTAMP  -- our receipt time; the two differ and that matters
  request_id          STRING
  idempotency_key     STRING
  livemode            BOOLEAN    -- always false
  payload             STRING     -- raw JSON, never parsed in Bronze
  _source_file        STRING
```

Bronze is append-only and never modified. The four quirks Silver must handle, each with a test:

| Quirk | Real Stripe behavior | Silver must |
|---|---|---|
| **At-least-once delivery** | The same `evt_` id can arrive more than once | Dedupe on `event_id`; assert idempotency |
| **Out-of-order arrival** | `charge.dispute.created` can land before `payment_intent.succeeded` | Order by `created`, not `ingested_at`; tolerate a missing parent and reconcile later |
| **API-version drift** | Different `api_version` values carry different field shapes | Quarantine unknown shapes to a `_rejected` table rather than failing the batch |
| **Integer minor units** | `amount: 1250` means $12.50; zero-decimal currencies (JPY) do not | Normalize to decimal using a currency exponent table; a quality expectation asserts no naive /100 |

That table alone answers the JD's *"data quality gates, freshness monitoring, and fail-safe
behavior built in from day one."*

## 4. Core objects (Stripe-shaped)

Field lists are the subset needed here, not the full API surface.

**customer** — `id (cus_)`, `created`, `email`, `metadata`, plus simulator-only
`country`, `risk_segment`, `verification_level`, `home_lat`, `home_long`.

**payment_intent** — `id (pi_)`, `amount`, `currency`, `status`
(`requires_payment_method` → `requires_confirmation` → `requires_action` → `processing` →
`succeeded` / `canceled`), `customer`, `payment_method`, `created`, `latest_charge`, `metadata`.
The status ladder gives real lifecycle events rather than a single row per transaction.

**charge** — `id (ch_)`, `amount`, `amount_refunded`, `currency`, `customer`, `created`, `paid`,
`refunded`, `disputed`, `failure_code`, `payment_method_details.card` (`brand`, `country`,
`funding`, `last4`, `network`), and `outcome` (`network_status`, `reason`, `risk_level`,
`risk_score`, `seller_message`, `type`).

> `outcome.risk_score` is worth calling out: it models a **platform-native baseline score**. The
> demo beat becomes *"here are the cases our network-aware model catches that the baseline score
> missed, and here is what it cost us in false declines to get them."* A comparison against a
> baseline is a far better result than a standalone number.

**dispute** — `id (dp_)`, `charge`, `amount`, `reason` (`fraudulent`, `product_not_received`,
`duplicate`, `unrecognized`, `subscription_canceled`, `credit_not_processed`, `general`),
`status` (`warning_needs_response` → `needs_response` → `under_review` → `won` / `lost`),
`created`, `evidence_details.due_by`.

> Disputes replace v1's `chargebacks` table and improve the label story materially. The delayed,
> noisy label is no longer a modeling convenience — it is how the real object behaves. `reason`
> gives friendly fraud for free: `fraudulent` is fraud, `product_not_received` and
> `subscription_canceled` mostly are not. And `status` means the label **matures**: a dispute is
> not resolved until won or lost, so as-of-time label state is genuinely three-valued
> (unknown / provisional / final). That is the strongest point-in-time story in the project.

**account** *(Stripe Connect — this is the merchant model)* — `id (acct_)`, `created`,
`business_type`, `country`, `charges_enabled`, `payouts_enabled`, `requirements.currently_due`,
`requirements.disabled_reason`, `capabilities`, `external_account` (bank), plus simulator-only
`owner_id`, `merchant_category`, `baseline_daily_volume`, `baseline_avg_ticket`, `persona`.

> Connect maps onto the v1 merchant model exactly, and better: `charges_enabled` /
> `payouts_enabled` / `requirements` *are* verification status, and a bust-out merchant ends with
> payouts paused — a real, recognizable outcome rather than an invented flag.

**payment_method**, **refund**, **balance_transaction**, **radar.early_fraud_warning** — thin, as
needed. The EFW object is a useful early risk signal that arrives before a dispute does.

## 5. Agentic extension

Stripe's own schema has no agent identity object, so this layer is designed rather than mapped.
Model it on the **concepts** that are stable across every agentic-payment scheme — delegated
mandate, agent identity, attestation, delegation chain — not on any one protocol's field names.

> Per the stack map in §0, the live schemes most relevant here are **Visa TAP** and **ERC-8004** /
> **DID+VCs** at Layer 2 (identity and attestation), and **AP2** at Layer 3 (mandates). **Verify
> current specs before citing any by name in an interview.** Designing to the shared concepts —
> identity, attestation, mandate, delegation — keeps the model correct regardless of which spec
> wins, and that design choice is itself worth stating out loud.

**agent**
```text
agent_id, operator, agent_version, first_seen,
attestation_level      -- none | self_asserted | operator_attested | issuer_verified
attestation_issuer, attestation_expires_at
```

**mandate** — the user's delegated authority; the central object in agentic payments
```text
mandate_id, customer_id, agent_id,
issued_at, expires_at, revoked_at,
max_amount_per_txn, max_amount_total, max_txn_count,
allowed_merchant_categories, allowed_merchants,
requires_human_confirmation_above,
single_use, parent_mandate_id      -- delegation chain
```

**agent_session** — the chain of actions leading to a payment
```text
session_id, agent_id, customer_id, started_at, ended_at,
user_intent_present     BOOLEAN   -- did a human actually ask for this?
merchant_ids_visited, tool_calls_count, injection_flag
```

**Extension to `payment_intent.metadata`** — where agentic context rides in reality:
`agent_id`, `mandate_id`, `session_id`, `attestation_token_hash`, `human_confirmed`.

Using `metadata` rather than inventing top-level fields is deliberate and correct: it is how this
data actually travels today, and it forces Silver to promote metadata into typed columns — another
piece of real work.

**Initiation channel** — a single column on `payment_intent` that carries a surprising amount of
analytical weight, and covers Layer 6 without implementing it:

```text
initiation_channel:
  human_initiated    -- a person checks out; classic risk model applies
  agent_delegated    -- an agent acts under a mandate on a human's behalf (Layers 3-5)
  agent_to_agent     -- machine-speed, no human in the loop, ever (Layer 6: x402, MPP, paid MCP)
```

Each channel has a genuinely different risk profile, and saying so is the analytical insight the
project is built to demonstrate:

| Channel | Typical amount | Velocity | Human recourse | What breaks |
|---|---|---|---|---|
| `human_initiated` | Normal | Human-paced | Dispute rights | Nothing — baseline |
| `agent_delegated` | Normal | Fast bursts | Dispute rights, but *who* disputes? | Velocity thresholds; intent attribution |
| `agent_to_agent` | Micropayments | Machine-speed, continuous | Often none | Per-transaction scoring economics collapse |

That last row is the sharpest observation available here: **when payments are sub-cent and
continuous, scoring every transaction individually costs more than the fraud it prevents.** The
answer is to score the *agent and the mandate* rather than the transaction, and to sample the
transaction stream. That is precisely the thesis the whole project is named for, and it falls out
of the channel dimension for the cost of one column.

## 6. Agentic fraud scenarios

These are native to agent-initiated payments and have no analogue in card fraud. They are the
differentiated half of the project.

**F — Mandate scope violation.** Agent transacts outside its delegated scope: over
`max_amount_per_txn`, outside `allowed_merchant_categories`, after `expires_at`, or past
`max_txn_count`. *Features:* `amount_over_mandate_ratio`, `category_in_mandate`,
`mandate_age_vs_expiry`, `mandate_txn_count_used`.

**G — Prompt-injection-induced purchase.** A merchant page injects instructions; the agent buys
something the user never asked for. *Signature:* `user_intent_present = false`, short session,
first-time merchant, purchase early in the session. *Features:* `intent_signal_absent`,
`session_duration_to_purchase`, `merchant_first_seen_in_session`, `tool_calls_before_purchase`.

**H — Agent impersonation.** An unattested agent claims a known operator's identity.
*Features:* `attestation_level`, `attestation_expired`, `operator_claim_vs_verified`,
`agent_first_seen_days`.

**I — Delegation chain abuse.** A sub-agent transacts beyond the parent mandate's scope.
*Features:* `delegation_depth`, `child_scope_exceeds_parent`, `parent_mandate_revoked`.

**J — Agent velocity.** Agents transact orders of magnitude faster than humans, so every
human-tuned velocity threshold is wrong. *Features:* `agent_txn_count_1m`,
`agent_unique_merchants_5m`, `agent_vs_human_velocity_ratio`.

**K — Mandate replay.** A single-use mandate or token reused. *Features:* `mandate_use_count`,
`single_use_violated`, `token_reuse_interval`.

Two things this buys the project:

- **A second trust score.** `agent_trust_score` reuses the merchant-trust machinery with different
  inputs — attestation level, mandate compliance history, injection incidence, velocity profile,
  network position. Cheap, because the framework already exists.
- **A third decision outcome.** The policy layer gains **STEP_UP** — pause and require human
  confirmation — alongside APPROVE / REVIEW / DECLINE. That is real behavior in agentic payment
  schemes, and it demos better than a binary decline: *"the mandate allowed $200, the agent asked
  for $340, so we didn't decline — we asked the human."*

## 7. Scope: what has to give

This is more work than the current Day 1–2. Be honest about it rather than absorbing it silently.

**Recommended trade — cap total scenarios at six plus one held out, and make three of them
agentic:**

| Keep | Cut / fold | Add |
|---|---|---|
| A — Account takeover | ~~D — Merchant collusion~~ → fold the shared-bank/owner mechanic into C, which already produces the same graph edges | F — Mandate scope violation |
| B — Card testing (cheap, and it contrasts well with agent velocity J) | | G — Prompt-injection purchase |
| C — Fraud ring (drives the graph features) | | H — Agent impersonation |
| E — Bust-out merchant (now ends in `payouts_enabled = false`) | | |
| Held out: refund abuse | | |

Scenarios I, J, K become stretch. Three agentic scenarios are enough to carry the thesis.

**Schedule delta:**
- **Day 0** gains the Stripe test-mode capture (half day). It fits, because Day 0 is currently light.
- **Day 1** gains agent / mandate / session entity generation (~2 hours).
- **Day 2** loses scenario D, gains F, G, H — roughly net neutral.
- **Day 3** gets materially harder and more valuable: real dedup, out-of-order handling, metadata
  promotion, currency normalization, schema quarantine.
- **Day 4** gains mandate-compliance and attestation features (~2 hours) and `agent_trust_score`
  (cheap — reuses merchant trust machinery).
- **Day 6** gains STEP_UP in the policy layer (~1 hour).

Net: roughly **plus one day**, concentrated in Day 3, which is the day whose output the target job
cares about most. Worth it. If the week can't absorb it, the thing to cut is `demo`-scale volume,
not this.

## 8. Open decisions

1. **Real Stripe test-mode capture, or schema-from-docs only?** Recommend real capture — it is half
   a day and it converts a stated JD gap into a demonstrated one. Requires a free Stripe account
   and a webhook endpoint (the Stripe CLI's `stripe listen --forward-to` handles local forwarding).
2. **How prominent is the agentic half?** Recommend co-equal: the pitch becomes *"fraud and trust
   for a payments platform where a growing share of transactions are initiated by AI agents rather
   than humans."* That is more differentiated than merchant fraud scoring, which is a crowded genre.
3. **Rename?** `TrustGraph` still fits, and the agent layer arguably makes the graph framing more
   apt, not less. No change recommended.
