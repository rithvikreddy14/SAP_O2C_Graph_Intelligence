"""
Ingest all 19 JSONL tables from the SAP O2C dataset into SQLite.

Usage (from backend/ directory):
    python scripts/ingest.py

Source: C:\\Users\\rithv\\Downloads\\sap-o2c-data\\
Each subfolder = one table. Multiple part-*.jsonl files per table.
"""

import os
import sys
import json
import sqlite3
import glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import SOURCE_DATA, DB_PATH

TABLES = [
    "billing_document_cancellations",
    "billing_document_headers",
    "billing_document_items",
    "business_partner_addresses",
    "business_partners",
    "customer_company_assignments",
    "customer_sales_area_assignments",
    "journal_entry_items_accounts_receivable",
    "outbound_delivery_headers",
    "outbound_delivery_items",
    "payments_accounts_receivable",
    "plants",
    "product_descriptions",
    "product_plants",
    "product_storage_locations",
    "products",
    "sales_order_headers",
    "sales_order_items",
    "sales_order_schedule_lines",
]


def load_jsonl_files(folder: Path) -> list[dict]:
    """Read all part-*.jsonl files in a folder and return list of dicts."""
    records = []
    files = sorted(glob.glob(str(folder / "part-*.jsonl")))
    if not files:
        # Also try .json extension
        files = sorted(glob.glob(str(folder / "*.jsonl")))
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return records


def infer_columns(records: list[dict]) -> list[str]:
    """Get union of all keys across first 200 records."""
    cols: dict[str, None] = {}
    for rec in records[:200]:
        for k in rec.keys():
            cols[k] = None
    return list(cols.keys())


def create_table(con: sqlite3.Connection, table: str, columns: list[str]) -> None:
    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    con.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs})')


def insert_records(con: sqlite3.Connection, table: str, columns: list[str], records: list[dict]) -> int:
    if not records:
        return 0
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT OR REPLACE INTO "{table}" ({col_names}) VALUES ({placeholders})'

    batch = []
    for rec in records:
        row = tuple(str(rec.get(c, "")) if rec.get(c) is not None else None for c in columns)
        batch.append(row)
        if len(batch) >= 5000:
            con.executemany(sql, batch)
            batch = []
    if batch:
        con.executemany(sql, batch)
    return len(records)


def add_indexes(con: sqlite3.Connection) -> None:
    """Add indexes on the most-queried foreign key columns."""
    indexes = [
        ("sales_order_items",       "SalesOrder"),
        ("outbound_delivery_items", "DeliveryDocument"),
        ("outbound_delivery_items", "ReferenceSDDocument"),
        ("billing_document_items",  "BillingDocument"),
        ("billing_document_items",  "SalesOrder"),
        ("journal_entry_items_accounts_receivable", "ReferenceDocument"),
        ("payments_accounts_receivable", "AccountingDocument"),
        ("product_storage_locations", "Material"),
        ("product_storage_locations", "Plant"),
        ("product_plants",          "Material"),
        ("product_descriptions",    "Material"),
    ]
    for table, col in indexes:
        idx_name = f"idx_{table}_{col}"
        try:
            con.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table}" ("{col}")')
        except Exception:
            pass


def main():
    source = Path(SOURCE_DATA)
    if not source.exists():
        print(f"ERROR: Source data folder not found: {source}")
        print("Update SOURCE_DATA in .env to point to your sap-o2c-data folder")
        sys.exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")

    total_rows = 0

    for table in TABLES:
        folder = source / table
        if not folder.exists():
            print(f"  [skip] {table} — folder not found")
            continue

        print(f"  [load] {table}…", end=" ", flush=True)
        records = load_jsonl_files(folder)

        if not records:
            print("0 records")
            continue

        columns = infer_columns(records)
        create_table(con, table, columns)
        n = insert_records(con, table, columns, records)
        con.commit()
        total_rows += n
        print(f"{n:,} rows, {len(columns)} columns")

    print("\n[indexes] Adding query indexes…")
    add_indexes(con)
    con.commit()
    con.close()

    print(f"\n Done! {total_rows:,} total rows → {DB_PATH}")
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"   Database size: {db_size:.1f} MB")


if __name__ == "__main__":
    main()