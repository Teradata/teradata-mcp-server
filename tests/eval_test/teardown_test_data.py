"""
Drops the eval tables from EVALS_DATABASE.

Usage:
    python teardown_test_data.py
"""

from __future__ import annotations

import os

import teradatasql
from dotenv import load_dotenv

load_dotenv()

TABLES = ["evals_employees", "evals_orders"]


def main() -> None:
    db = os.environ.get("EVALS_DATABASE")
    if not db:
        raise SystemExit("EVALS_DATABASE env var is not set — check your .env file")

    print(f"Connecting to Teradata (host={os.environ.get('TERADATA_HOST')}) ...")
    with teradatasql.connect(
        host=os.environ["TERADATA_HOST"],
        user=os.environ["TERADATA_USER"],
        password=os.environ["TERADATA_PASSWORD"],
    ) as con:
        with con.cursor() as cur:
            for table in TABLES:
                try:
                    cur.execute(f"DROP TABLE {db}.{table}")
                    print(f"  Dropped {db}.{table}")
                except Exception as exc:
                    print(f"  Skipped {db}.{table}: {exc}")

    print("Teardown complete.")


if __name__ == "__main__":
    main()
