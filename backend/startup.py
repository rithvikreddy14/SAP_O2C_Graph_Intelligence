import os, sys

BASE     = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
DB_PATH  = os.path.join(DATA_DIR, "database.db")
CACHE    = os.path.join(DATA_DIR, "graph_cache.json")

os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(DB_PATH):
    print("[startup] No database.db found — running ingest...")
    import subprocess
    r = subprocess.run([sys.executable, "scripts/ingest.py"], cwd=BASE)
    if r.returncode != 0:
        print("[startup] ingest.py failed — continuing anyway")

if not os.path.exists(CACHE):
    print("[startup] No graph_cache.json — running build_graph...")
    import subprocess
    r = subprocess.run([sys.executable, "scripts/build_graph.py"], cwd=BASE)
    if r.returncode != 0:
        print("[startup] build_graph.py failed — continuing anyway")

print("[startup] Done.")