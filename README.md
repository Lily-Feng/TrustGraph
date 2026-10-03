# TrustGraph — Autonomous Decisions You Can Audit

> **Fraud, risk, and trust infrastructure for agentic commerce, where an increasing share of financial transactions are initiated and settled by AI agents rather than humans.**

[![CI and deploy GitHub Pages](https://github.com/Lily-Feng/TrustGraph/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/Lily-Feng/TrustGraph/actions/workflows/deploy-pages.yml)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue)](https://lily-feng.github.io/TrustGraph/)

---

## 🌐 Live Interactive Demo

Experience the autonomous shopping agent simulation with real-time protocol inspection, 8-dimensional trust scoring, and cryptographic audit trail:

👉 **[https://lily-feng.github.io/TrustGraph/](https://lily-feng.github.io/TrustGraph/)**

---

## 💡 The Core Idea

### The Shift to Agentic Commerce
In traditional e-commerce, a human navigates a storefront, verifies prices, clicks "checkout", and submits multi-factor authentication (3D Secure, SMS OTP, biometric confirmation). Fraud models optimize for detecting unauthorized human access (stolen cards, account takeovers, session anomalies).

In **agentic commerce**, the interaction model is inverted:
1. **Delegated Authority**: A human issues a broad, natural-language goal (e.g., *"Plan Lily's graduation party under $3,500 before 2 PM"*).
2. **Autonomous Negotiation**: AI shopping agents search, negotiate, and coordinate with specialized merchant agents across disparate platforms.
3. **Machine-Speed Execution**: Transactions occur programmatically in sub-second intervals without direct human presence during each checkout.

### The Problem TrustGraph Solves
When autonomous agents spend real money, traditional checkout protections fail:
- **Mandate Drift & Scope Creep**: How do we ensure an agent cannot exceed delegated spending limits or buy outside its approved domain?
- **Phantom & Malicious Merchants**: How can an agent evaluate whether an unknown digital vendor has verified operational reliability and fulfillment consistency?
- **Execution & Latency Risk**: In multi-vendor transactions (e.g. food, cake, venue, gifts), how do we prevent catastrophic failures where one vendor defaults and compromises the entire event?
- **Sybil Reputation Games**: Star ratings and reviews are easily gamed by synthetic LLM bots. Trust must be grounded in cryptographically verifiable fulfillment histories.

---

## 🏛️ Where TrustGraph Sits in the Agentic Payments Stack

TrustGraph is designed against an **8-layer architectural decomposition** of autonomous agent payments:

| Layer | Protocol / Domain | TrustGraph's Relationship |
|:---|:---|:---|
| **L1** | **Agent Communication & Discovery** (A2A, MCP, Agent Cards) | Upstream infrastructure. How agents discover each other. |
| **L2** | **Agent Identity, Trust & Reputation** (DID, Verifiable Credentials, ERC-8004) | **Consumed as Input**. Validates identity and cryptographic attestations. |
| **L3** | **Mandate, Consent & Policy** (AP2, delegated spending limits, revocation) | **Consumed as Input**. Bound spending limits and policy constraints. |
| **L4** | **Offer, Quote & Transaction Coordination** (UCP, ACP, Stripe-shaped manifests) | **The Transaction Flow**. Machine manifests, carts, and quote coordination. |
| **L5** | **Payment Authentication, Risk & Compliance** (*TrustGraph MDT*) | 🎯 **THIS IS TRUSTGRAPH**. Fraud scoring, multi-dimensional merchant evaluation, AML/KYC checks, transaction integrity. |
| **L6** | **Machine-Speed Payment Protocols** (x402, MPP, Stripe Agentic Rails) | **Execution Channel**. Programmatic, machine-speed payments and paid tool calls. |
| **L7** | **Settlement Rails** (Cards, ACH, Wires, Stablecoins) | Downstream financial rails. How value physically settles. |
| **L8** | **Post-Transaction Lifecycle** (Disputes, Chargebacks, Smart Escrow) | 🔄 **Closes the Feedback Loop**. Milestone escrow settlements and delivery feedback update future MDT trust scores. |

> **The One-Sentence Pitch:**  
> *TrustGraph is a Layer 5 risk and authentication engine that consumes Layer 2 attestations and Layer 3 mandates, scores Layer 4 transaction flow via 8-dimensional Merchant Digital Twins, and closes the trust loop with Layer 8 milestone disputes.*

---

## ⚙️ Key Architectural Pillars

### 1. Merchant Digital Twin (MDT)
The MDT is an 8-dimensional, continuously calibrated trust model for merchants:
- 🚚 **Delivery (Del)**: Punctuality, tracking fidelity, and milestone SLA adherence.
- 🏷️ **Price (Pri)**: Price stability, hidden surcharge absence, and quote fidelity.
- 📜 **Contract (Con)**: Fulfillment fidelity to negotiated specifications and item requirements.
- ⏱️ **Latency (Lat)**: Responsiveness in machine-to-machine quote negotiation and confirmation.
- ⚠️ **Dispute (Dis)**: Historical chargeback, cancellation, and dispute incidence rates.
- 🔄 **Consistency (Con)**: Repeated performance stability over high transaction volumes.
- 💬 **Comms (Com)**: Machine protocol compatibility, structured updates, and exception handling.
- 🤝 **Resolution (Res)**: Proactive resolution speed and fair customer remediation track record.

### 2. AP2 Payment Mandates
Delegated payment authority is never an open-ended blank check. TrustGraph enforces signed **AP2 Mandates**:
- Hard cumulative budget ceiling ($3,500.00).
- Single-transaction velocity caps ($1,500.00 per vendor).
- Strict milestone timing constraints (all deliverables confirmed before 2:00 PM).
- Category whitelisting and real-time mandate revocation.

### 3. Smart Milestone Escrow
Funds are not released unconditionally upfront. Payments are held in **programmable escrow contracts** divided into verifiable milestones:
`Deposit Locked` ➔ `Fulfillment / Delivery Proof Verified` ➔ `Funds Released`.
If a vendor fails an SLA, escrow protections permit rapid mitigation or dispute resolution.

### 4. Verifiable Audit Trail
Every autonomous evaluation produces a timestamped, cryptographically verifiable log record. Financial compliance officers, risk underwriters, and consumers can trace:
- Why merchant A was selected over merchant B (MDT score 0.93 vs 0.74).
- How the AP2 mandate was enforced at the byte level.
- Exact proof of settlement and feedback emission into the MDT data lake.

---

## 🎬 Demo Scenario: Lily's Graduation Party

The interactive demo simulates an autonomous shopping agent orchestrating a complex, multi-merchant event:

```text
Step 0: Awaiting Demo Start
  └── TrustGraph enabled, payment cards ready, MDT radar primed

Step 1: User Prompt
  └── "Plan Lily's graduation party next Saturday. Elegant, warm, under $3,500, ready before 2 PM."

Step 2: Context & AP2 Mandate Binding
  └── $3,500 budget cap, 4 required categories, 2 PM delivery constraint cryptographically signed.

Step 3: UCP Merchant Research
  └── Autonomous scanning across candidate Merchant Digital Twins in Setup, Catering, Bakery, and Gifts.

Step 4: MDT Score Evaluation
  └── Top merchants selected: BrightCap Events (0.93), Golden Tassel Cakes (0.89), Harvest Table (0.87), Keepsake Lane (0.85).

Step 5: TrustGraph Payment Authentication
  └── 4 payments authorized totaling $3,460.00 ($40 under budget; all under single-merchant cap).

Step 6: Smart Milestone Escrow
  └── Funds locked into 4 milestone-based smart contracts with tokenized reputation telemetry.

Step 7: Delivery Verification & Closed Loop
  └── Deliveries verified on-site before 2 PM, escrow released, positive ratings written back to MDT lake.
```

---

## 🎮 Interactive Controls & Shortcuts

| Action | Control | Shortcut |
|:---|:---|:---:|
| **Run / Pause Demo** | Play button in header | <kbd>Space</kbd> |
| **Next / Previous Step** | Arrow buttons in header | <kbd>→</kbd> / <kbd>←</kbd> |
| **Direct Step Jump** | Click step progress pills | <kbd>0</kbd> – <kbd>7</kbd> |
| **Toggle Event Log Full Height** | `⚡ EVENT LOG` tab or `⤢` expand icon | Click |
| **Toggle Sound Effects** | Speaker icon in top navigation | Click |
| **Inspect Payloads & Modals** | Click any protocol card or merchant row | Click / <kbd>Esc</kbd> to close |

---

## 💻 Local Development

This repository contains a zero-dependency, high-performance static web application built with vanilla JavaScript, modern CSS Grid/Flexbox, and the Web Audio API.

### Run locally:
```bash
# Clone the repository
git clone https://github.com/Lily-Feng/TrustGraph.git
cd TrustGraph

# Start a local web server (Python 3)
python3 -m http.server 8080
```
Open **`http://localhost:8080`** in your browser.

### Validate site assets and syntax:
```bash
node --check app.js
node .github/scripts/validate-site.mjs
```

---

## 📄 License

MIT © [Lily Feng](https://github.com/Lily-Feng)
