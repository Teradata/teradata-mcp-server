"""
Creates the two eval tables in EVALS_DATABASE and populates them with sample data.

evals_employees  — used by: base, qlty (stats), plot (radar)
evals_orders     — used by: base, qlty (missing/negative values), plot (line/pie/polar)

Usage:
    python setup_test_data.py
    python setup_test_data.py --drop-first   # drop and recreate if tables already exist
"""

from __future__ import annotations

import argparse
import os

import teradatasql
from dotenv import load_dotenv

load_dotenv()

CREATE_EMPLOYEES = """
CREATE TABLE {db}.evals_employees (
    employee_id   INTEGER        NOT NULL,
    name          VARCHAR(100)   NOT NULL,
    department    VARCHAR(50)    NOT NULL,
    salary        DECIMAL(10,2),
    region        VARCHAR(50)    NOT NULL,
    hire_date     DATE           NOT NULL,
    manager_id    INTEGER,
    PRIMARY KEY (employee_id)
)
"""

CREATE_ORDERS = """
CREATE TABLE {db}.evals_orders (
    order_id         INTEGER        NOT NULL,
    customer_name    VARCHAR(100)   NOT NULL,
    order_date       DATE           NOT NULL,
    ship_date        DATE,
    amount           DECIMAL(10,2)  NOT NULL,
    product_category VARCHAR(50)    NOT NULL,
    quantity         INTEGER        NOT NULL,
    PRIMARY KEY (order_id)
)
"""

EMPLOYEES_DATA = [
    (1,  "Alice Johnson",  "Engineering", 95000.00, "North", "2019-03-15", None),
    (2,  "Bob Smith",      "Sales",       72000.00, "South", "2020-07-01", 1),
    (3,  "Carol White",    "HR",          68000.00, "East",  "2018-11-20", 1),
    (4,  "David Brown",    "Finance",     85000.00, "West",  "2021-01-10", 1),
    (5,  "Eva Martinez",   "Engineering", 102000.00,"North", "2017-06-05", 1),
    (6,  "Frank Lee",      "Sales",       69500.00, "South", "2022-04-18", 2),
    (7,  "Grace Kim",      "Marketing",   77000.00, "East",  "2020-09-30", 1),
    (8,  "Henry Adams",    "Finance",     91000.00, "West",  "2019-12-01", 4),
    (9,  "Isla Thompson",  "HR",          None,     "North", "2023-02-14", 3),
    (10, "Jack Wilson",    "Engineering", 88000.00, "South", "2016-08-22", 5),
]

ORDERS_DATA = [
    (1001, "Acme Corp",     "2024-01-05", "2024-01-08",  1250.00, "Electronics",  3),
    (1002, "Beta Ltd",      "2024-01-12", "2024-01-15",  -200.00, "Clothing",     1),  # refund
    (1003, "Gamma Inc",     "2024-02-03", None,           875.50, "Food",         5),  # not shipped
    (1004, "Delta Co",      "2024-02-17", "2024-02-20",  3400.00, "Electronics",  2),
    (1005, "Epsilon LLC",   "2024-03-01", "2024-03-04",   560.00, "Books",        8),
    (1006, "Zeta Partners", "2024-03-15", None,          -150.00, "Clothing",     1),  # refund, not shipped
    (1007, "Eta Group",     "2024-04-02", "2024-04-06",  2100.00, "Sports",       4),
    (1008, "Theta Corp",    "2024-04-20", "2024-04-23",   930.00, "Food",         6),
    (1009, "Iota Inc",      "2024-05-08", None,          1780.00, "Electronics",  1),  # not shipped
    (1010, "Kappa Ltd",     "2024-05-25", "2024-05-28",  4200.00, "Sports",       7),
]


def get_connection():
    host = os.environ["TERADATA_HOST"]
    user = os.environ["TERADATA_USER"]
    password = os.environ["TERADATA_PASSWORD"]
    return teradatasql.connect(host=host, user=user, password=password)


def drop_tables(cursor, db: str) -> None:
    for table in ("evals_employees", "evals_orders"):
        try:
            cursor.execute(f"DROP TABLE {db}.{table}")
            print(f"  Dropped {db}.{table}")
        except Exception:
            pass  # table didn't exist


def create_and_populate(cursor, db: str) -> None:
    print(f"Creating {db}.evals_employees ...")
    cursor.execute(CREATE_EMPLOYEES.format(db=db))

    for row in EMPLOYEES_DATA:
        cursor.execute(
            f"INSERT INTO {db}.evals_employees VALUES (?,?,?,?,?,?,?)", [list(row)]
        )
    print(f"  Inserted {len(EMPLOYEES_DATA)} rows")

    print(f"Creating {db}.evals_orders ...")
    cursor.execute(CREATE_ORDERS.format(db=db))

    for row in ORDERS_DATA:
        cursor.execute(
            f"INSERT INTO {db}.evals_orders VALUES (?,?,?,?,?,?,?)", [list(row)]
        )
    print(f"  Inserted {len(ORDERS_DATA)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create eval test tables in Teradata")
    parser.add_argument("--drop-first", action="store_true", help="Drop tables before recreating")
    args = parser.parse_args()

    db = os.environ.get("EVALS_DATABASE", "").strip()
    if not db:
        raise SystemExit("EVALS_DATABASE env var is not set — check your .env file")

    print(f"Connecting to Teradata (host={os.environ.get('TERADATA_HOST')}) ...")
    with get_connection() as con:
        with con.cursor() as cur:
            if args.drop_first:
                print("Dropping existing tables ...")
                drop_tables(cur, db)
            create_and_populate(cur, db)

    print("\nSetup complete. Run evals with: python run_evals.py")


if __name__ == "__main__":
    main()
