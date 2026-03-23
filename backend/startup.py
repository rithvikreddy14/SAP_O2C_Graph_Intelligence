import os, sys, subprocess

BASE     = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
DB_PATH  = os.path.join(DATA_DIR, "database.db")
CACHE    = os.path.join(DATA_DIR, "graph_cache.json")

os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(DB_PATH):
    print("[startup] database.db not found — running ingest.py ...")
    r = subprocess.run([sys.executable, "scripts/ingest.py"], cwd=BASE)
    if r.returncode != 0:
        print("[startup] ERROR: ingest.py failed")
        sys.exit(1)
    print("[startup] ingest.py complete")

if not os.path.exists(CACHE):
    print("[startup] graph_cache.json not found — running build_graph.py ...")
    r = subprocess.run([sys.executable, "scripts/build_graph.py"], cwd=BASE)
    if r.returncode != 0:
        print("[startup] ERROR: build_graph.py failed")
        sys.exit(1)
    print("[startup] build_graph.py complete")

print("[startup] All data ready.")