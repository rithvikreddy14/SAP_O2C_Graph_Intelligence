import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_cors import CORS

# Module-level graph state — loaded once on startup
_graph_json: dict = {"nodes": [], "links": []}
_graph_nx = None


def get_graph_json() -> dict:
    return _graph_json


def get_graph_nx():
    return _graph_nx


def create_app() -> Flask:
    global _graph_json, _graph_nx

    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Load or build graph on startup
    from app.graph_builder import build_graph, graph_to_json, load_graph_cache
    from config import DB_PATH

    cached = load_graph_cache()
    if cached:
        print(f"[startup] Loaded graph from cache: {len(cached['nodes'])} nodes")
        _graph_json = cached
    elif os.path.exists(DB_PATH):
        print("[startup] Building graph from database…")
        _graph_nx = build_graph()
        _graph_json = graph_to_json(_graph_nx)
        print(f"[startup] Graph ready: {len(_graph_json['nodes'])} nodes, {len(_graph_json['links'])} edges")
    else:
        print("[startup] WARNING: database.db not found. Run scripts/ingest.py first.")

    from app.routes import bp
    app.register_blueprint(bp)

    return app