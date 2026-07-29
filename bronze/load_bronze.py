"""
TransactSafe — Bronze Layer Ingestion
=======================================
Loads raw CSVs (as-is, no cleaning) into DuckDB, adding audit columns
so every row can be traced back to when and from where it was ingested.

This is intentionally "dumb" — no cleaning, no validation. That happens
in the silver layer. Bronze exists purely to preserve an untouched,
auditable copy of the source data.

Run:
    python load_bronze.py            # loads into local file duckdb (bronze.duckdb)
    python load_bronze.py --motherduck   # loads into your MotherDuck cloud instance
"""

import argparse
import glob
from datetime import datetime
from pathlib import Path

import duckdb

SOURCE_DIR = Path("../data_generator/bronze_source")


def get_connection(use_motherduck: bool):
    if use_motherduck:
        # Uses MOTHERDUCK_TOKEN env var automatically (already set in your ~/.bashrc)
        con = duckdb.connect("md:transactsafe")
        print("Connected to MotherDuck (cloud) — database 'transactsafe'")
    else:
        con = duckdb.connect("bronze.duckdb")
        print("Connected to local DuckDB file 'bronze.duckdb'")
    return con


def load_table(con, table_name: str, csv_path: Path):
    ingested_at = datetime.now().isoformat()
    source_file = csv_path.name

    con.execute(f"""
        CREATE OR REPLACE TABLE bronze_{table_name} AS
        SELECT
            *,
            '{ingested_at}' AS _ingested_at,
            '{source_file}' AS _source_file
        FROM read_csv_auto('{csv_path}')
    """)

    count = con.execute(f"SELECT COUNT(*) FROM bronze_{table_name}").fetchone()[0]
    print(f"  -> bronze_{table_name}: {count} rows loaded from {csv_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--motherduck", action="store_true", help="Load into MotherDuck instead of local file")
    args = parser.parse_args()

    con = get_connection(args.motherduck)

    tables = {
        "customers": SOURCE_DIR / "customers.csv",
        "accounts": SOURCE_DIR / "accounts.csv",
        "transactions": SOURCE_DIR / "transactions.csv",
    }

    for table_name, csv_path in tables.items():
        if not csv_path.exists():
            print(f"WARNING: {csv_path} not found, skipping. Did you run generate_data.py first?")
            continue
        load_table(con, table_name, csv_path)

    print("\nBronze layer load complete.")
    print("Tables created: bronze_customers, bronze_accounts, bronze_transactions")

    con.close()


if __name__ == "__main__":
    main()
