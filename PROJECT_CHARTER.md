# TransactSafe: Banking Fraud Detection Data Pipeline

**Author:** Muhammad Obaid Ullah
**Role:** Data Engineer (Portfolio Project)
**Status:** In Development

---

## 1. Problem Statement

Financial institutions process millions of transactions daily. Regulators (under frameworks like the EU's Anti-Money Laundering Directives and EBA guidelines) require institutions to:

- Detect suspicious transaction patterns in near-real-time (rapid repeated transfers, geographic anomalies, unusual amount spikes)
- Maintain clean, auditable data lineage from raw ingestion through to reporting, so any flagged case can be traced back to its source record
- Produce reliable, tested data marts that compliance and fraud analyst teams can query without needing to understand the underlying pipeline

Most public "data engineering portfolio projects" stop at moving data from A to B. This project instead simulates the actual constraints a fraud/compliance data team operates under: auditability, data quality enforcement, and business-usable outputs — not just a working pipeline, but a *trustworthy* one.

## 2. Goals

1. Ingest raw transaction data with zero transformation (bronze layer) to preserve an auditable source of truth
2. Clean, validate, and deduplicate data with explicit, testable rules (silver layer)
3. Produce business-ready marts: risk-scored transactions, flagged accounts, monthly compliance summaries (gold layer)
4. Orchestrate the pipeline on a schedule, with basic failure handling
5. Expose results through a dashboard usable by a non-technical fraud analyst
6. Document every architectural decision so the project is defensible in an interview, not just demonstrable

## 3. Non-Goals (explicitly out of scope)

- Real-time streaming (this is a batch pipeline — streaming is a valid v2 extension, noted in "Future Work")
- Actual regulatory compliance certification (this is a simulation for portfolio/learning purposes, not a production compliance system)
- Machine learning model development for fraud scoring (risk scoring here uses rule-based heuristics — ML scoring is a natural v2 extension)

## 4. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────┐
│  Synthetic   │────▶│    BRONZE    │────▶│    SILVER     │────▶│    GOLD    │
│  Data Gen    │     │ (raw ingest, │     │  (cleaned,    │     │ (risk marts,│
│  (Python/    │     │  audit cols) │     │   validated,  │     │  compliance │
│   Faker)     │     │              │     │   deduped)    │     │  summaries) │
└──────────────┘     └──────────────┘     └───────────────┘     └────────────┘
                             ▲                     ▲                    │
                             │                     │                    ▼
                      Airflow DAG            dbt models            Streamlit
                     (orchestration)        (transform + test)      Dashboard
```

**Storage:** DuckDB (local) + MotherDuck (cloud) — chosen over Postgres/Snowflake for this project because it offers genuine cloud data warehouse behavior (SQL, cloud storage, shareable) at zero cost, letting the project stay fully reproducible for anyone reviewing it without needing paid infrastructure.

**Orchestration:** Apache Airflow — the de facto industry standard for batch orchestration; used here to demonstrate DAG design, scheduling, and dependency management rather than running scripts manually.

**Transformation:** dbt — chosen because it enforces version-controlled, tested SQL transformations and automatically generates data lineage documentation, which directly supports the auditability goal in Section 1.

**Dashboard:** Streamlit — chosen for fast deployment to a free public URL, so anyone reviewing this project (recruiter, committee, client) can interact with results without installing anything.

## 5. Data Model Overview

**Source (synthetic):**
- `accounts` — account_id, customer_id, account_type, open_date, country
- `transactions` — transaction_id, account_id, amount, currency, timestamp, merchant, transaction_type, geo_location
- `customers` — customer_id, name (fake), risk_profile_seed, country

**Bronze:** Raw copies of the above with added `_ingested_at`, `_source_file` columns.

**Silver:**
- `stg_transactions` — deduplicated, type-cast, nulls handled, referential integrity enforced (every transaction maps to a valid account)
- `stg_accounts`, `stg_customers` — cleaned equivalents

**Gold:**
- `fct_flagged_transactions` — transactions matching rule-based risk criteria (velocity checks, amount thresholds, geographic mismatches)
- `dim_account_risk_scores` — aggregated risk score per account
- `mart_monthly_compliance_summary` — monthly aggregated view for a compliance report

## 6. Key Architectural Decisions & Tradeoffs

| Decision | Alternative Considered | Why This Choice |
|---|---|---|
| DuckDB/MotherDuck over Postgres | Postgres (local) | Zero-cost cloud warehouse behavior; easier for reviewers to access without setup |
| Rule-based risk scoring over ML | Trained fraud classifier | Keeps scope focused on data engineering rigor rather than ML modeling; documented as a clear v2 extension |
| Batch (Airflow) over streaming (Kafka) | Kafka + streaming | Reflects the most common real-world DE hiring need (batch is still dominant); streaming noted as future work to show awareness without overscoping |
| Synthetic data over public dataset | Public Kaggle fraud dataset | Synthetic data lets me control data quality issues intentionally (duplicates, nulls, malformed records), which is necessary to demonstrate the silver-layer cleaning logic meaningfully |

## 7. Success Criteria

- [ ] Pipeline runs end-to-end on a schedule via Airflow without manual intervention
- [ ] dbt test suite passes with documented coverage (not null, unique, relationships, accepted values)
- [ ] Dashboard is publicly deployed and loads without errors
- [ ] dbt docs site is deployed and shows full lineage graph
- [ ] README tells a complete story: problem → architecture → decisions → results → future work

## 8. Future Work (v2 ideas, not built now)

- Real-time streaming ingestion (Kafka/Kinesis)
- ML-based risk scoring model
- Role-based access control simulation for the dashboard
- CI/CD pipeline (GitHub Actions) running dbt tests on every PR

---

*This charter is a living document — I will update it if architectural decisions change during the build.*

