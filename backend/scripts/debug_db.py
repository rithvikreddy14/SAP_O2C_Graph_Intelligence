"""
Run this to inspect what's actually in your database.
Usage: python scripts/debug_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlite3
from config import DB_PATH

print(f"DB path: {DB_PATH}")
print(f"DB exists: {os.path.exists(DB_PATH)}\n")

con = sqlite3.connect(DB_PATH)

# List all tables
tables = con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
print(f"=== Tables found: {len(tables)} ===")
for (t,) in tables:
    count = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    cols = [r[1] for r in con.execute(f"PRAGMA table_info('{t}')").fetchall()]
    print(f"\n{t} ({count} rows)")
    print(f"  Columns: {', '.join(cols)}")

con.close()