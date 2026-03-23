import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def run_query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return rows as list of dicts. Max 100 rows."""
    con = get_connection()
    try:
        rows = con.execute(sql, params).fetchmany(100)
        return [dict(r) for r in rows]
    finally:
        con.close()


def table_exists(table: str) -> bool:
    con = get_connection()
    try:
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()
        return row is not None
    finally:
        con.close()