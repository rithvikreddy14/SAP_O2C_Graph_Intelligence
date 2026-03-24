# SAP O2C Graph Intelligence

> A graph-based data exploration and natural language query system for SAP Order-to-Cash business data — built with React, Flask, NetworkX, SQLite, and Groq LLM.

---

## 1. Project Title

**SAP O2C Graph Intelligence**
*Graph-Based Data Modeling and Conversational Query System for Order-to-Cash Processes*

---

## 2. Overview

Real-world SAP business data is spread across isolated tables — orders, deliveries, invoices, payments — with no intuitive way to trace how a transaction flows end-to-end. This project unifies that fragmented relational data into an interactive knowledge graph and layers a conversational AI interface on top of it.

Users can visually explore the full Order-to-Cash (O2C) process, click on any entity node to inspect its properties and connections, and ask natural language questions like *"which products appear in the most billing documents?"* or *"trace the full flow for billing document 91150187"*. The system translates those questions into SQL, executes them against the real dataset, and returns grounded, data-backed answers — never hallucinated responses.

This is not a static dashboard or a Q&A chatbot. It is a live, queryable intelligence layer over structured SAP data.

---

## 3. Objectives

- Ingest 19 heterogeneous SAP JSONL tables into a unified SQLite database
- Model the business data as a directed property graph using NetworkX
- Build an interactive force-directed graph visualization for data exploration
- Implement a two-pass LLM pipeline: natural language → SQL → execute → narrate
- Enforce strict domain guardrails to prevent off-topic or hallucinated responses
- Deploy a full-stack web application accessible via a public demo link
- Document all architectural decisions, prompting strategies, and tradeoffs

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (React)                       │
│                                                             │
│  ┌─────────────────────┐    ┌──────────────────────────┐   │
│  │   Graph Canvas       │    │      Chat Panel           │   │
│  │  react-force-graph   │    │  NL Input → Answer + SQL  │   │
│  │  880 nodes, 807 edges│    │  Result Table + Highlight │   │
│  └──────────┬──────────┘    └────────────┬─────────────┘   │
│             │  /api/graph                │  /api/chat        │
└─────────────┼────────────────────────────┼──────────────────┘
              │                            │
┌─────────────▼────────────────────────────▼──────────────────┐
│                   Flask Backend (Python)                      │
│                                                             │
│  routes.py → guardrails.py → query_engine.py               │
│                                    │                         │
│           ┌────────────────────────┼──────────────┐         │
│           │                        │              │         │
│     graph_builder.py          schema.py      db.py          │
│     NetworkX DiGraph          LLM prompts   SQLite          │
│           │                        │              │         │
│    graph_cache.json           Groq API      database.db    │
└─────────────────────────────────────────────────────────────┘
              │
┌─────────────▼──────────────┐
│   Source Data               │
│   19 × JSONL part files     │
│   C:\...\sap-o2c-data\      │
└────────────────────────────┘
```

**Data flow summary:**

1. `ingest.py` reads all JSONL part files → loads into SQLite (21,393 rows, 3 MB)
2. `build_graph.py` reads SQLite → builds NetworkX graph → caches as `graph_cache.json`
3. Flask serves the graph JSON to the React frontend on startup
4. User asks a question → `guardrails.py` checks domain → `query_engine.py` calls Groq
5. Groq generates SQL → SQLite executes it → Groq narrates the results
6. Frontend receives `{ answer, sql, rows }` → renders answer, shows SQL badge, highlights graph nodes

---

## 5. Dataset Description

**Source:** *https://drive.google.com/file/d/1UqaLbFaveV-3MEuiUrzKydhKmkeC1iAL/view*
**Format:** JSONL part files (multiple `part-*.jsonl` per table)
**Total:** 19 tables, 21,393 rows, 3 MB SQLite database

| Table | Rows | Description |
|---|---|---|
| `sales_order_headers` | 100 | Core sales orders with customer, amount, status |
| `sales_order_items` | 167 | Line items per sales order with material and quantity |
| `sales_order_schedule_lines` | 179 | Delivery schedule lines per order item |
| `outbound_delivery_headers` | 86 | Outbound shipment records |
| `outbound_delivery_items` | 137 | Items per delivery, links back to sales order |
| `billing_document_headers` | 163 | Invoice headers with amount and type |
| `billing_document_items` | 245 | Line items per billing document |
| `billing_document_cancellations` | 80 | Cancelled billing documents |
| `journal_entry_items_accounts_receivable` | 123 | GL journal entries linked to billing docs |
| `payments_accounts_receivable` | 120 | Payment records clearing journal entries |
| `business_partners` | 8 | Customer/partner master data |
| `business_partner_addresses` | 8 | Address details per partner |
| `customer_company_assignments` | 8 | Customer ↔ company code mapping |
| `customer_sales_area_assignments` | 28 | Customer sales area configuration |
| `plants` | 44 | Plant master data |
| `products` | 69 | Product/material master |
| `product_descriptions` | 69 | Multi-language product descriptions |
| `product_plants` | 3,036 | Product ↔ plant assignments |
| `product_storage_locations` | 16,723 | Inventory per storage location (largest table) |

**Important:** All column names in the dataset are `camelCase` (e.g. `salesOrder`, `billingDocument`, `referenceSdDocument`), not PascalCase.

---

## 6. Graph Data Modeling

The dataset is modeled as a **directed property graph** using NetworkX `DiGraph`.

### Node types (9 entity types, 880 nodes)

| Node type | Source table | ID prefix | Color |
|---|---|---|---|
| `SalesOrder` | `sales_order_headers` | `so_` | Blue |
| `SalesOrderItem` | `sales_order_items` | `soitem_` | Light blue |
| `OutboundDelivery` | `outbound_delivery_headers` | `del_` | Green |
| `BillingDocument` | `billing_document_headers` | `bill_` | Amber |
| `JournalEntry` | `journal_entry_items_accounts_receivable` | `je_` | Violet |
| `Payment` | `payments_accounts_receivable` | `pay_` | Pink |
| `BusinessPartner` | `business_partners` | `bp_` | Cyan |
| `Product` | `products` | `mat_` | Red |
| `Plant` | `plants` | `plant_` | Orange |

### Edge types (807 edges)

| Relationship | From → To | How linked |
|---|---|---|
| `HAS_ITEM` | SalesOrder → SalesOrderItem | `salesOrder` FK |
| `HAS_DELIVERY` | SalesOrder → OutboundDelivery | `outbound_delivery_items.referenceSdDocument` |
| `HAS_INVOICE` | SalesOrder → BillingDocument | `billing_document_items.referenceSdDocument` |
| `HAS_JOURNAL_ENTRY` | BillingDocument → JournalEntry | `journal_entry_items.referenceDocument` |
| `HAS_PAYMENT` | JournalEntry → Payment | `accountingDocument` |
| `PLACED_ORDER` | BusinessPartner → SalesOrder | `soldToParty` FK |
| `ORDERED_IN` | Product → SalesOrderItem | `material` FK |

### Complete O2C flow

```
BusinessPartner
    └── PLACED_ORDER ──▶ SalesOrder
                              ├── HAS_ITEM ──▶ SalesOrderItem ◀── ORDERED_IN ── Product
                              ├── HAS_DELIVERY ──▶ OutboundDelivery
                              └── HAS_INVOICE ──▶ BillingDocument
                                                        └── HAS_JOURNAL_ENTRY ──▶ JournalEntry
                                                                                        └── HAS_PAYMENT ──▶ Payment
```

### Design decisions

- **NetworkX in-memory** for graph traversal and visualization serving — no Neo4j required
- **SQLite for analytics** — LLMs generate SQL far more reliably than Cypher
- **Pre-built JSON cache** (`graph_cache.json`) so Flask startup is instant
- Nodes carry all relevant properties as graph attributes for the popup inspector

---

## 7. Tech Stack

### Backend

| Concern | Choice | Reason |
|---|---|---|
| API framework | Flask 3.0 | Lightweight, zero-config, easy to deploy |
| Graph library | NetworkX 3.2 | In-memory directed graph, no database setup |
| Database | SQLite (built-in) | No server, single file, LLM generates SQL well |
| Data ingestion | Pandas + Python | Reads JSONL part files, infers schema dynamically |
| LLM provider | Groq (free tier) | Fast inference, generous free limits |
| LLM model | `llama-3.1-8b-instant` | Low latency, good SQL generation |
| CORS | flask-cors | Frontend on different port |

### Frontend

| Concern | Choice | Reason |
|---|---|---|
| Framework | React 18 + TypeScript | Component model, type safety |
| Bundler | Vite 5 | Fast HMR, simple proxy config |
| Graph visualization | react-force-graph-2d | Canvas-based, handles 1000+ nodes smoothly |
| Icons | lucide-react | Clean, consistent icon set |
| Fonts | Syne + DM Sans + DM Mono | Distinctive, professional look |
| Deployment | Vercel (frontend) + Railway (backend) | Free tiers, GitHub deploy |

---

## 8. Workflow / Pipeline

### Data ingestion (run once)

```
sap-o2c-data/
  billing_document_headers/part-*.jsonl
  sales_order_headers/part-*.jsonl
  ... (19 tables)
          │
          ▼  scripts/ingest.py
   SQLite database.db
   (21,393 rows, 3 MB)
          │
          ▼  scripts/build_graph.py
   graph_cache.json
   (880 nodes, 807 edges)
```

### Runtime query pipeline

```
User types NL question
        │
        ▼
guardrails.py (Layer 1)
  keyword allowlist + regex blocklist
  → rejects off-topic instantly (no LLM call)
        │ passes
        ▼
query_engine.py — Pass 1
  system prompt = full 19-table camelCase schema
  LLM returns <sql>SELECT ...</sql>
        │
        ▼
db.py — SQLite execution
  runs query, returns up to 100 rows
        │ on error → Pass 2b: self-healing (LLM fixes query)
        ▼
query_engine.py — Pass 2
  LLM receives: question + sql + rows[:30]
  returns plain-English narration
        │
        ▼
Frontend receives { answer, sql, rows }
  → renders answer in chat
  → shows collapsible SQL badge with row count
  → shows inline result table (≤10 rows)
  → maps row values to graph node IDs → highlights + zooms
```

---

## 9. LLM Integration

### Model

`llama-3.1-8b-instant` via Groq API (free tier, ~200ms latency)

### Two-pass pipeline (`app/query_engine.py`)

**Pass 1 — SQL generation**

The system prompt includes:
- Full schema for all 19 tables with exact camelCase column names
- All foreign key relationships described in plain English
- The complete O2C join path
- Rules: SQLite dialect only, wrap SQL in `<sql>...</sql>`, LIMIT 100

The LLM returns the SQL query plus a brief explanation.

**Pass 2 — Result narration**

The narration prompt instructs the LLM to:
- Answer directly using specific values from the results
- Stay under 150 words
- Never say "based on the results" or repeat the SQL

**Self-healing on SQL error**

If SQLite raises an error, a third LLM call sends the error message back and asks for a corrected query — before ever returning a failure to the user.

### Prompting strategy

The schema description in `schema.py` is the single most critical file for query accuracy. It took multiple iterations to get right — the key lessons were:

- Column names must be exactly as they appear in the database (camelCase, not PascalCase)
- Foreign key paths must be spelled out explicitly, not left to inference
- The O2C join chain must be described as a concrete sequence of tables
- Temperature is set to 0.1 for deterministic SQL output

---

## 10. Guardrails

Domain restriction is enforced at two independent layers.

### Layer 1 — Pre-LLM filter (`app/guardrails.py`)

A fast Python check before any LLM call:

- **Regex blocklist:** explicit off-topic patterns — poems, jokes, weather, recipes, general coding questions, geography
- **Keyword allowlist:** 40+ O2C domain terms — `salesOrder`, `billing`, `delivery`, `material`, `plant`, `journal`, `payment`, `fiscalYear`, etc.
- **Short query passthrough:** queries under 5 words pass through (LLM handles them)

This layer adds zero latency for off-topic questions and prevents unnecessary API consumption.

### Layer 2 — LLM system prompt

The system prompt explicitly instructs the LLM:

> *"If the question is NOT about this dataset (e.g. general knowledge, jokes, weather, coding help), respond ONLY with: 'This system is designed to answer questions related to the provided SAP O2C dataset only.'"*

The two-layer approach means off-topic queries never reach the LLM, and ambiguous queries that slip through Layer 1 are still caught by the LLM's own instruction.

**Rejection example:**

```
User: "What is the capital of France?"
System: "This system is designed to answer questions related to the
         provided SAP O2C dataset only."
```

---

## 11. Example Queries

The system is capable of answering a wide range of analytical questions:

| Query | Type |
|---|---|
| Which products appear in the most billing documents? | Aggregation + JOIN |
| Trace the full flow for billing document 91150187 | Multi-table JOIN chain |
| Find sales orders that were delivered but never billed | LEFT JOIN + NULL check |
| Are there billing documents with no journal entry? | Broken flow detection |
| Show top 10 customers by total net order amount | Ranking + aggregation |
| Which plants handle the most deliveries? | Group by + count |
| 91150187 - Find the journal entry number linked to this | Point lookup |
| What is the total revenue by sales organization? | Financial aggregation |
| Which sales orders have been cancelled? | Status filter |
| Show me products with inventory across multiple storage locations | Multi-join |

---

## 12. Key Features

**Graph visualization**
- Force-directed graph with 880 nodes and 807 edges
- 9 node types, each with a distinct vivid color
- Click any node to open a floating property inspector
- Navigate between connected nodes from the popup
- Auto-zoom and pan to highlighted nodes after a query result

**Conversational query interface**
- Natural language input with Enter-to-submit
- 6 pre-built suggestion chips on first load
- Collapsible SQL viewer with row count badge
- Inline result table for small result sets (≤10 rows)
- Animated loading state (typing dots)

**Graph highlighting**
- Query results are mapped to graph node IDs and highlighted
- Non-matching nodes fade to 15% opacity
- Highlighted nodes show glowing outer rings and visible labels
- Connecting edges of highlighted nodes turn blue
- Map auto-pans and zooms to center highlighted nodes in view

**Infrastructure**
- Graph pre-cached as JSON — instant load on Flask startup
- Vite dev proxy — no CORS issues in development
- Self-healing SQL — LLM auto-corrects its own query on error
- WAL mode SQLite for concurrent read performance

---

## 13. Optional Enhancements

The following bonus features have been implemented beyond the base requirements:

| Feature | Status | Details |
|---|---|---|
| NL to SQL translation | ✅ Implemented | Two-pass Groq pipeline |
| Graph node highlighting from query | ✅ Implemented | Maps row values to node IDs, zooms to them |
| SQL query display | ✅ Implemented | Collapsible badge with row count |
| Self-healing SQL | ✅ Implemented | Third LLM call on error to fix query |
| Conversation memory | ✅ Implemented | Full message history in chat panel |
| Graph cache | ✅ Implemented | Pre-built JSON for fast startup |
| Node navigation | ✅ Implemented | Click neighbors to traverse the graph |
| Result tables | ✅ Implemented | Inline for ≤10 rows |
| Suggestion chips | ✅ Implemented | 6 example queries on first load |

---

## 14. Project Structure

```
sap-o2c-graph/
│
├── README.md                        ← this file
│
├── backend/
│   ├── run.py                       ← Flask entry point: python run.py
│   ├── config.py                    ← env vars, paths (reads .env)
│   ├── requirements.txt             ← Python dependencies
│   ├── .env                         ← GROQ_API_KEY (not committed)
│   │
│   ├── app/
│   │   ├── __init__.py              ← app factory, loads graph on startup
│   │   ├── routes.py                ← /graph  /chat  /node/:id  /health  /stats
│   │   ├── graph_builder.py         ← SQLite → NetworkX → graph_cache.json
│   │   ├── query_engine.py          ← NL → SQL (Groq) → execute → narrate
│   │   ├── guardrails.py            ← two-layer domain restriction
│   │   ├── db.py                    ← SQLite connection (WAL mode)
│   │   └── schema.py                ← SYSTEM_PROMPT, NARRATION_PROMPT, schema strings
│   │
│   ├── scripts/
│   │   ├── ingest.py                ← JSONL → SQLite (run once)
│   │   └── build_graph.py           ← build + cache graph (run once)
│   │
│   └── data/                        ← generated, not committed
│       ├── database.db              ← 3 MB SQLite (21,393 rows)
│       └── graph_cache.json         ← 880 nodes, 807 edges
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts               ← proxies /api/* → localhost:5000
    ├── tsconfig.json
    │
    └── src/
        ├── App.tsx                  ← root layout, all state management
        ├── api.ts                   ← fetch helpers: fetchGraph, fetchNode, sendChat
        ├── types.ts                 ← GraphNode, GraphLink, Message, ChatResponse
        ├── main.tsx                 ← React entry point
        ├── styles.css               ← full white-theme CSS (no UI library)
        │
        └── components/
            ├── GraphView.tsx        ← force-graph canvas, highlight + zoom logic
            ├── ChatPanel.tsx        ← NL chat UI, suggestion chips, highlight mapping
            ├── NodeDetail.tsx       ← floating node popup with properties + neighbors
            ├── SqlBadge.tsx         ← collapsible SQL viewer with row count
            └── GraphLegend.tsx      ← node type color legend overlay
```

---

## 15. Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free Groq API key from [console.groq.com](https://console.groq.com)
- The SAP O2C dataset at *https://drive.google.com/file/d/1UqaLbFaveV-3MEuiUrzKydhKmkeC1iAL/view*

### Step 1 — Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2 — Configure environment

Edit `backend/.env`:

```env
GROQ_API_KEY=gsk_your_key_here
SOURCE_DATA=https://drive.google.com/file/d/1UqaLbFaveV-3MEuiUrzKydhKmkeC1iAL/view
DB_PATH=data/database.db
GRAPH_CACHE=data/graph_cache.json
MAX_GRAPH_NODES=3000
```

### Step 3 — Ingest dataset (run once)

```bash
python scripts/ingest.py
```

Expected output:
```
[load] billing_document_headers… 163 rows, 14 columns
[load] sales_order_headers… 100 rows, 24 columns
... (19 tables)
Done! 21,393 total rows → data/database.db
Database size: 3.0 MB
```

### Step 4 — Build graph cache (run once)

```bash
python scripts/build_graph.py
```

Expected output:
```
Building graph from database…
  Graph built: 880 nodes, 807 edges
  Cached: 880 nodes, 807 edges → data/graph_cache.json
```

### Step 5 — Start Flask backend

```bash
python run.py
```

Flask runs at `http://localhost:5000`

### Step 6 — Start React frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` — open this in your browser.

### Production build

```bash
# Frontend
cd frontend
npm run build
# Produces dist/ — deploy to Vercel

# Backend
# Deploy to Railway with Procfile:
# web: uvicorn run:app --host 0.0.0.0 --port $PORT
```

---

## 16. API / Environment Setup

### Flask API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check, returns node + edge counts |
| `GET` | `/graph` | Full graph JSON (`{ nodes, links }`) |
| `GET` | `/node/<id>` | Node properties + neighbor list |
| `POST` | `/chat` | `{ "message": "..." }` → `{ answer, sql, rows }` |
| `GET` | `/stats` | Row counts for all 19 tables |

### Example chat request

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Which products appear in the most billing documents?"}'
```

### Example chat response

```json
{
  "answer": "The top product is S8907367039280 with 22 appearances in billing documents...",
  "sql": "SELECT material, COUNT(billingDocument) as count FROM billing_document_items GROUP BY material ORDER BY count DESC LIMIT 10",
  "rows": [
    { "material": "S8907367039280", "count": 22 },
    { "material": "S8907367008620", "count": 22 }
  ]
}
```

### Environment variables reference

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | required | Groq API key from console.groq.com |
| `SOURCE_DATA` | `C:\Users\rithv\Downloads\sap-o2c-data` | Path to JSONL dataset |
| `DB_PATH` | `data/database.db` | SQLite database output path |
| `GRAPH_CACHE` | `data/graph_cache.json` | Graph JSON cache path |
| `MAX_GRAPH_NODES` | `3000` | Max nodes loaded into graph |
| `FLASK_DEBUG` | `1` | Enable Flask debug mode |

---

## 17. Screenshots / Demo

### Graph overview
The force-directed graph shows all 880 nodes organized by the SAP O2C business relationships. Each node type has a distinct color (blue = SalesOrder, amber = BillingDocument, violet = JournalEntry, green = OutboundDelivery, pink = Payment, etc.). The left panel shows a live count legend.

### Natural language query + highlighting
When a user asks *"Which products appear in the most billing documents?"*, the system generates SQL, executes it, and returns a narrated answer. The matching product nodes are highlighted in the graph with glowing rings; all other nodes fade to near-invisible. The map auto-pans and zooms to center the highlighted nodes.

### Node inspector popup
Clicking any node opens a floating popup showing all its properties and up to 8 connected neighbors. Clicking a neighbor navigates to that node's popup, enabling manual graph traversal.

### SQL transparency
Every answer includes a collapsible SQL badge showing the exact query that was executed, along with the row count. This ensures full transparency and auditability of every answer.

---

## 18. Demo Link

> **Live demo:** *https://sap-o2-c-graph-intelligence.vercel.app/*
>
> **GitHub repository:** *https://github.com/rithvikreddy14/SAP_O2C_Graph_Intelligence*

To deploy:

```bash
# Frontend → Vercel
# 1. Push frontend/ to GitHub
# 2. Import project at vercel.com
# 3. Set VITE_API_URL environment variable to your Railway URL

# Backend → Railway
# 1. Push backend/ to GitHub
# 2. Create new project at railway.app
# 3. Add environment variables from .env
# 4. Add Procfile: web: python run.py
```

---

## 19. Challenges & Solutions

### Challenge 1 — Column name mismatch (camelCase vs PascalCase)

**Problem:** The initial code assumed PascalCase column names (`SalesOrder`, `OverallSDProcessStatus`) but the actual SAP export uses camelCase (`salesOrder`, `overallDeliveryStatus`). This caused `sqlite3.OperationalError: no such column` on every query.

**Solution:** Ran `PRAGMA table_info()` on every table and rebuilt the schema description and graph builder with exact column names from the real database. Also added a `debug_db.py` script to introspect all table schemas programmatically.

### Challenge 2 — Graph node highlighting not working

**Problem:** The React frontend was passing raw database values (e.g. `"S8907367039280"`) to the highlight function, but graph nodes have prefixed IDs (e.g. `"mat_S8907367039280"`). The sets never intersected.

**Solution:** Built a `buildHighlightIds()` function in `ChatPanel.tsx` that maps each known database field name to its graph node prefix — `salesOrder` → `so_`, `billingDocument` → `bill_`, `material` → `mat_`, etc.

### Challenge 3 — Graph not zooming to highlighted nodes

**Problem:** After highlighting, the map stayed at the same position. The user had to manually find the highlighted dots.

**Solution:** Added a `useEffect` in `GraphView.tsx` that fires when `highlightIds` changes. It computes the bounding box centroid of all highlighted nodes' `x,y` simulation coordinates, then calls `fg.centerAt(cx, cy, 700)` followed by `fg.zoom(zoom, 500)` with a 200ms delay. Handles both settled and still-simulating graphs.

### Challenge 4 — LLM generating invalid SQL

**Problem:** Early prompts produced SQL with wrong column names, missing JOINs, or SQLite-incompatible syntax.

**Solution:** Implemented a self-healing third pass — if SQLite throws an error, the error message is sent back to the LLM with a request to fix the query. Also lowered temperature to 0.1 for more deterministic output, and added explicit JOIN path documentation in the system prompt.

### Challenge 5 — Graph visualization performance

**Problem:** Loading all 21,393 rows as nodes would make the frontend unusable.

**Solution:** The graph builder samples intelligently — full coverage of transactional entities (sales orders, billing docs, payments) but capped totals via `MAX_GRAPH_NODES`. The result is 880 meaningful nodes that show all the important O2C relationships without overwhelming the force simulation.

---

## 20. Future Improvements

**Short term**
- Add conversation memory with sliding context window so follow-up questions reference previous answers
- Implement semantic search over node properties using embeddings (find "all German customers" even if Germany is stored as `DE`)
- Add graph clustering to visually group nodes by type or business area
- Export query results as CSV directly from the UI

**Medium term**
- Replace `llama-3.1-8b-instant` with a fine-tuned SQL model for higher JOIN accuracy
- Add streaming responses from the LLM so the answer appears word-by-word
- Implement graph diff view — highlight what changed between two date ranges
- Add user authentication and query history persistence

**Long term**
- Migrate analytics layer from SQLite to DuckDB for columnar query performance on larger datasets
- Add a graph database (Neo4j or Memgraph) as an optional backend for Cypher-based traversal queries
- Support uploading arbitrary SAP exports — auto-detect schema and build graph dynamically
- Multi-tenant deployment with per-organization dataset isolation

---

