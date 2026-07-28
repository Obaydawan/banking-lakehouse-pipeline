"""
TransactSafe — Synthetic Banking Data Generator
=================================================
Generates realistic banking data (customers, accounts, transactions) with
INTENTIONAL data quality issues and embedded fraud patterns, so the
silver-layer cleaning logic and gold-layer risk scoring have something
meaningful to work with.

Output: three CSV files landed into ./bronze_source/
    - customers.csv
    - accounts.csv
    - transactions.csv

Run:
    python generate_data.py
"""

import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path("bronze_source")
OUTPUT_DIR.mkdir(exist_ok=True)

N_CUSTOMERS = 2000
N_ACCOUNTS = 3000
N_TRANSACTIONS = 50000
DAYS_OF_HISTORY = 90

COUNTRIES = ["PK", "US", "GB", "DE", "AE", "FR", "NL", "IN", "CN", "SA"]
HIGH_RISK_COUNTRIES = ["NG", "KP", "IR"]  # for geographic anomaly patterns
MERCHANT_CATEGORIES = [
    "Grocery", "Electronics", "Travel", "Restaurant", "Utilities",
    "Online Retail", "Fuel", "Healthcare", "Entertainment", "ATM Withdrawal",
]

# ---------------------------------------------------------------------------
# 1. CUSTOMERS
# ---------------------------------------------------------------------------
def generate_customers(n):
    rows = []
    for i in range(n):
        customer_id = f"CUST{i:06d}"
        risk_seed = np.random.choice([0, 1], p=[0.95, 0.05])  # 5% seeded as higher-risk profiles

        name = fake.name()
        # Intentional data quality issue: ~2% missing names
        if random.random() < 0.02:
            name = None

        rows.append({
            "customer_id": customer_id,
            "name": name,
            "country": random.choice(COUNTRIES),
            "signup_date": fake.date_between(start_date="-3y", end_date="-90d"),
            "risk_profile_seed": risk_seed,
        })

    df = pd.DataFrame(rows)

    # Intentional data quality issue: a handful of exact duplicate rows
    dup_sample = df.sample(n=int(n * 0.01), random_state=1)
    df = pd.concat([df, dup_sample], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# 2. ACCOUNTS
# ---------------------------------------------------------------------------
def generate_accounts(customers_df, n):
    rows = []
    customer_ids = customers_df["customer_id"].unique().tolist()

    for i in range(n):
        account_id = f"ACC{i:07d}"
        customer_id = random.choice(customer_ids)

        open_date = fake.date_between(start_date="-3y", end_date="-30d")

        rows.append({
            "account_id": account_id,
            "customer_id": customer_id,
            "account_type": random.choice(["Checking", "Savings", "Business"]),
            "open_date": open_date,
            "country": random.choice(COUNTRIES),
            "status": np.random.choice(["Active", "Closed", "Frozen"], p=[0.92, 0.06, 0.02]),
        })

    df = pd.DataFrame(rows)

    # Intentional data quality issue: ~1% of accounts reference a customer_id that doesn't exist
    # (simulates late-arriving / orphaned records — silver layer must catch this)
    orphan_idx = df.sample(n=int(n * 0.01), random_state=2).index
    df.loc[orphan_idx, "customer_id"] = [f"CUST{900000+i}" for i in range(len(orphan_idx))]

    return df


# ---------------------------------------------------------------------------
# 3. TRANSACTIONS (with embedded fraud patterns)
# ---------------------------------------------------------------------------
def generate_transactions(accounts_df, n, days):
    rows = []
    account_ids = accounts_df["account_id"].unique().tolist()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    for i in range(n):
        transaction_id = str(uuid.uuid4())
        account_id = random.choice(account_ids)
        ts = fake.date_time_between(start_date=start_date, end_date=end_date)

        amount = round(np.random.lognormal(mean=4.0, sigma=1.2), 2)  # realistic right-skewed spend distribution
        currency = "USD"
        merchant_category = random.choice(MERCHANT_CATEGORIES)
        country = random.choice(COUNTRIES)
        txn_type = random.choice(["Purchase", "Transfer", "Withdrawal", "Deposit"])

        rows.append({
            "transaction_id": transaction_id,
            "account_id": account_id,
            "timestamp": ts,
            "amount": amount,
            "currency": currency,
            "merchant_category": merchant_category,
            "transaction_type": txn_type,
            "country": country,
        })

    df = pd.DataFrame(rows)

    # --- Embedded fraud pattern 1: velocity fraud (rapid repeated transactions) ---
    velocity_accounts = random.sample(account_ids, k=15)
    velocity_rows = []
    for acc in velocity_accounts:
        burst_start = fake.date_time_between(start_date=start_date, end_date=end_date)
        for j in range(random.randint(6, 12)):
            velocity_rows.append({
                "transaction_id": str(uuid.uuid4()),
                "account_id": acc,
                "timestamp": burst_start + timedelta(minutes=j * 2),
                "amount": round(np.random.uniform(200, 900), 2),
                "currency": "USD",
                "merchant_category": "ATM Withdrawal",
                "transaction_type": "Withdrawal",
                "country": random.choice(COUNTRIES),
            })
    df = pd.concat([df, pd.DataFrame(velocity_rows)], ignore_index=True)

    # --- Embedded fraud pattern 2: geographic anomaly (high-risk country transactions) ---
    geo_accounts = random.sample(account_ids, k=25)
    geo_rows = []
    for acc in geo_accounts:
        geo_rows.append({
            "transaction_id": str(uuid.uuid4()),
            "account_id": acc,
            "timestamp": fake.date_time_between(start_date=start_date, end_date=end_date),
            "amount": round(np.random.uniform(1000, 5000), 2),
            "currency": "USD",
            "merchant_category": "Online Retail",
            "transaction_type": "Purchase",
            "country": random.choice(HIGH_RISK_COUNTRIES),
        })
    df = pd.concat([df, pd.DataFrame(geo_rows)], ignore_index=True)

    # --- Embedded fraud pattern 3: unusually large single transactions ---
    large_idx = df.sample(n=30, random_state=3).index
    df.loc[large_idx, "amount"] = np.round(np.random.uniform(10000, 50000, size=len(large_idx)), 2)

    # --- Intentional data quality issues ---
    # ~0.5% negative amounts (should be impossible — silver layer must catch)
    neg_idx = df.sample(n=int(len(df) * 0.005), random_state=4).index
    df.loc[neg_idx, "amount"] = -df.loc[neg_idx, "amount"]

    # ~0.3% null amounts
    null_idx = df.sample(n=int(len(df) * 0.003), random_state=5).index
    df.loc[null_idx, "amount"] = None

    # ~0.5% duplicate transaction_ids (simulates upstream retry/dedup failure)
    dup_idx = df.sample(n=int(len(df) * 0.005), random_state=6).index
    dup_rows = df.loc[dup_idx].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print("Generating customers...")
    customers_df = generate_customers(N_CUSTOMERS)
    customers_df.to_csv(OUTPUT_DIR / "customers.csv", index=False)
    print(f"  -> {len(customers_df)} rows written")

    print("Generating accounts...")
    accounts_df = generate_accounts(customers_df, N_ACCOUNTS)
    accounts_df.to_csv(OUTPUT_DIR / "accounts.csv", index=False)
    print(f"  -> {len(accounts_df)} rows written")

    print("Generating transactions (with embedded fraud patterns + data quality issues)...")
    transactions_df = generate_transactions(accounts_df, N_TRANSACTIONS, DAYS_OF_HISTORY)
    transactions_df.to_csv(OUTPUT_DIR / "transactions.csv", index=False)
    print(f"  -> {len(transactions_df)} rows written")

    print("\nDone. Files written to ./bronze_source/")
    print("Embedded patterns for later detection:")
    print("  - Velocity fraud: 15 accounts with rapid repeated withdrawals")
    print("  - Geographic anomaly: 25 accounts with high-risk-country transactions")
    print("  - Large transaction outliers: 30 transactions")
    print("  - Data quality issues: nulls, negatives, duplicates, orphaned foreign keys")


if __name__ == "__main__":
    main()

