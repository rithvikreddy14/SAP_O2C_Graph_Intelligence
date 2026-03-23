"""
Flask API routes:
  GET  /graph          → full graph JSON for frontend viz
  POST /chat           → NL query → SQL → narrated answer
  GET  /node/<id>      → node metadata + neighbors
  GET  /health         → liveness check
  GET  /stats          → dataset statistics
"""

import sqlite3
from flask import Blueprint, request, jsonify

from app.guardrails import is_domain_query, REJECTION_MSG
from app.query_engine import process_question
from app import get_graph_json, get_graph_nx
from app.db import get_connection

bp = Blueprint("api", __name__)


# ── Health ────────────────────────────────────────────────────────────────────

@bp.get("/health")
def health():
    gj = get_graph_json()
    return jsonify({
        "status": "ok",
        "nodes": len(gj.get("nodes", [])),
        "edges": len(gj.get("links", [])),
    })


# ── Graph ─────────────────────────────────────────────────────────────────────

@bp.get("/graph")
def get_graph():
    return jsonify(get_graph_json())


# ── Node detail ───────────────────────────────────────────────────────────────

@bp.get("/node/<path:node_id>")
def get_node(node_id: str):
    G = get_graph_nx()
    gj = get_graph_json()

    # Find node in graph JSON
    node_data = next((n for n in gj["nodes"] if n["id"] == node_id), None)

    if node_data is None:
        return jsonify({"error": "Node not found"}), 404

    # Get neighbors
    if G is not None:
        neighbor_ids = list(G.neighbors(node_id)) + list(G.predecessors(node_id))
        neighbor_ids = list(dict.fromkeys(neighbor_ids))[:40]
        neighbors = [n for n in gj["nodes"] if n["id"] in set(neighbor_ids)]
    else:
        # Fall back to scanning links
        neighbor_ids = set()
        for link in gj["links"]:
            if link["source"] == node_id:
                neighbor_ids.add(link["target"])
            elif link["target"] == node_id:
                neighbor_ids.add(link["source"])
        neighbors = [n for n in gj["nodes"] if n["id"] in neighbor_ids][:40]

    return jsonify({
        "node": node_data,
        "neighbors": neighbors,
    })


# ── Chat ──────────────────────────────────────────────────────────────────────

@bp.post("/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()

    if not message:
        return jsonify({"error": "message is required"}), 400

    # Layer 1: keyword guardrail
    if not is_domain_query(message):
        return jsonify({
            "answer": REJECTION_MSG,
            "sql": None,
            "rows": [],
        })

    # Layer 2 + execution: LLM pipeline
    result = process_question(message)
    return jsonify(result)


# ── Stats ─────────────────────────────────────────────────────────────────────

@bp.get("/stats")
def stats():
    """Return row counts for all tables — shown in the UI header."""
    tables = [
        "sales_order_headers", "sales_order_items", "outbound_delivery_headers",
        "outbound_delivery_items", "billing_document_headers", "billing_document_items",
        "billing_document_cancellations", "journal_entry_items_accounts_receivable",
        "payments_accounts_receivable", "business_partners", "business_partner_addresses",
        "customer_company_assignments", "customer_sales_area_assignments",
        "plants", "products", "product_descriptions",
        "product_plants", "product_storage_locations", "sales_order_schedule_lines",
    ]
    counts = {}
    try:
        con = get_connection()
        for t in tables:
            try:
                row = con.execute(f"SELECT COUNT(*) as c FROM {t}").fetchone()
                counts[t] = row["c"] if row else 0
            except Exception:
                counts[t] = 0
        con.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(counts)