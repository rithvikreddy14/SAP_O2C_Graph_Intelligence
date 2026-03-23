"""
Build and cache the NetworkX graph to data/graph_cache.json.
Run this after ingest.py so Flask starts faster.

Usage (from backend/ directory):
    python scripts/build_graph.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.graph_builder import build_graph, save_graph_cache
from config import DB_PATH

if not os.path.exists(DB_PATH):
    print(f"ERROR: {DB_PATH} not found. Run scripts/ingest.py first.")
    sys.exit(1)

print("Building graph from database…")
G = build_graph()
save_graph_cache(G)
print("Done.")