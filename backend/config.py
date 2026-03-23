import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()

# Only load .env if running locally (Railway sets vars directly)
if not os.getenv("RAILWAY_ENVIRONMENT"):
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

DATA_DIR = BASE_DIR / "data"

GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
SOURCE_DATA     = os.getenv("SOURCE_DATA", r"C:\Users\rithv\Downloads\sap-o2c-data")
DB_PATH         = str(BASE_DIR / os.getenv("DB_PATH", "data/database.db"))
GRAPH_CACHE     = str(BASE_DIR / os.getenv("GRAPH_CACHE", "data/graph_cache.json"))
MAX_GRAPH_NODES = int(os.getenv("MAX_GRAPH_NODES", 3000))

DATA_DIR.mkdir(exist_ok=True)

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not set — chat will not work")
else:
    print(f"[config] GROQ_API_KEY loaded (starts with: {GROQ_API_KEY[:8]}...)")