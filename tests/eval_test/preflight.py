"""Verify eval prerequisites before running live evals against Teradata."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

EVAL_TABLES = ("evals_employees", "evals_orders")


def check_eval_tables() -> list[str]:
    """Return human-readable errors; empty list means OK."""
    db = os.environ.get("EVALS_DATABASE", "").strip()
    if not db:
        return ["EVALS_DATABASE is not set — copy .env.example to .env and fill in values"]

    missing_env = [
        name
        for name in ("TERADATA_HOST", "TERADATA_USER", "TERADATA_PASSWORD")
        if not os.environ.get(name, "").strip()
    ]
    if missing_env:
        return [f"Missing Teradata env var(s): {', '.join(missing_env)}"]

    try:
        from setup_test_data import get_connection
    except ImportError as exc:
        return [f"Cannot import Teradata helpers: {exc}"]

    errors: list[str] = []
    try:
        with get_connection() as con:
            with con.cursor() as cur:
                for table in EVAL_TABLES:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {db}.{table}")
                        row_count = cur.fetchone()[0]
                    except Exception as exc:
                        errors.append(f"{db}.{table} is not accessible: {exc}")
                        continue
                    if row_count == 0:
                        errors.append(f"{db}.{table} exists but has no rows")
    except Exception as exc:
        errors.append(f"Cannot connect to Teradata ({os.environ.get('TERADATA_HOST')}): {exc}")

    if errors:
        errors.append("Fix with: uv run python setup_test_data.py")

    return errors


def run_preflight() -> None:
    errors = check_eval_tables()
    if not errors:
        db = os.environ.get("EVALS_DATABASE", "").strip()
        print(f"Preflight OK — {db}.evals_employees and {db}.evals_orders are ready.")
        return

    print("Preflight failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    run_preflight()


if __name__ == "__main__":
    main()
