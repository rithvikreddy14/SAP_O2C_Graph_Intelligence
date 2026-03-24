import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_cors import CORS

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

    from app.graph_builder import build_graph, graph_to_json, load_graph_cache
    from config import DB_PATH

    # Load synchronously so Gunicorn workers actually get the data!
    cached = load_graph_cache()
    if cached and len(cached.get("nodes", [])) > 0:
        print(f"[startup] Graph loaded from cache: {len(cached['nodes'])} nodes")
        _graph_json = cached
    elif os.path.exists(DB_PATH):
        print("[startup] Building graph from database...")
        _graph_nx = build_graph()
        _graph_json = graph_to_json(_graph_nx)
        print(f"[startup] Graph ready: {len(_graph_json['nodes'])} nodes")
    else:
        print("[startup] WARNING: database.db not found")

    from app.routes import bp
    app.register_blueprint(bp)

    return app