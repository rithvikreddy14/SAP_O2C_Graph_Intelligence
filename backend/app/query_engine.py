"""
Two-pass LLM pipeline:
  Pass 1: NL question  -> LLM generates <sql>...</sql>
  Pass 2: SQL results  -> LLM narrates answer in plain English
"""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import GROQ_API_KEY
from app.schema import SYSTEM_PROMPT, NARRATION_PROMPT
from app.db import run_query

_client = None
_MODEL  = "llama-3.1-8b-instant"

# Dangerous SQL patterns that should never reach SQLite
_DANGEROUS_SQL_PATTERNS = [
    r"SELECT\s+\*\s+FROM\s+\w+\s*(?:;|$)",   # bare SELECT * with no WHERE/LIMIT
    r"DROP\s+TABLE", r"DELETE\s+FROM", r"UPDATE\s+\w+\s+SET",
    r"INSERT\s+INTO", r"ALTER\s+TABLE", r"CREATE\s+TABLE",
]

def _init_client():
    global _client
    if _client is not None:
        return _client
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return None
    try:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
        return _client
    except Exception as e:
        print(f"[query_engine] Failed to init Groq client: {e}")
        return None


def _llm(messages: list, max_tokens: int = 1024) -> str:
    client = _init_client()
    if client is None:
        return (
            "LLM client not initialised. Please:\n"
            "1. Open backend/.env\n"
            "2. Replace 'your_groq_api_key_here' with your real key from https://console.groq.com\n"
            "3. Restart Flask (Ctrl+C then python run.py)"
        )
    resp = client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return resp.choices[0].message.content.strip()


def _extract_sql(text: str):
    m = re.search(r"<sql>(.*?)</sql>", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"(SELECT\s.+?)(?:;|$)", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _is_safe_sql(sql: str) -> tuple:
    """
    Returns (is_safe, reason).
    Blocks bare SELECT * and all write/DDL operations.
    """
    sql_upper = sql.upper().strip()

    # Must be a SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    # Block dangerous write patterns
    for pattern in _DANGEROUS_SQL_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE | re.DOTALL):
            return False, f"Query blocked for safety: matches pattern '{pattern}'"

    # Warn if no LIMIT — add one automatically
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return True, "no_limit"

    return True, "ok"


def _ensure_limit(sql: str, default: int = 100) -> str:
    """Add LIMIT if missing."""
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = sql.rstrip(";").rstrip() + f"\nLIMIT {default};"
    return sql


def process_question(question: str) -> dict:
    # Pass 1: generate SQL
    pass1_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": question},
    ]
    pass1_response = _llm(pass1_messages)

    if "LLM client not initialised" in pass1_response:
        return {"answer": pass1_response, "sql": None, "rows": [], "error": None}

    # Guardrail layer 2: LLM rejected the question
    if "designed to answer questions related to" in pass1_response.lower():
        return {"answer": pass1_response, "sql": None, "rows": [], "error": None}

    # LLM asked for clarification (vague query handling)
    if "please specify" in pass1_response.lower() and "<sql>" not in pass1_response.lower():
        return {"answer": pass1_response, "sql": None, "rows": [], "error": None}

    sql = _extract_sql(pass1_response)

    if not sql:
        return {"answer": pass1_response, "sql": None, "rows": [], "error": None}

    # Safety check on generated SQL
    is_safe, reason = _is_safe_sql(sql)
    if not is_safe:
        return {
            "answer": "The generated query was blocked for safety. Please rephrase your question with a specific entity (e.g. billing documents, sales orders, products).",
            "sql": sql,
            "rows": [],
            "error": reason,
        }

    # Auto-add LIMIT if missing
    if reason == "no_limit":
        sql = _ensure_limit(sql, default=100)

    # Execute SQL
    try:
        rows = run_query(sql)
    except Exception as e:
        # Self-healing: send error back to LLM to fix
        fix_messages = [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": question},
            {"role": "assistant", "content": pass1_response},
            {"role": "user",      "content": (
                f"That SQL raised this error: {e}\n"
                f"Check the column names against the schema. "
                f"Remember: plant column is in outbound_delivery_items, not outbound_delivery_headers. "
                f"Please produce a corrected query."
            )},
        ]
        fix_response = _llm(fix_messages)
        fixed_sql = _extract_sql(fix_response)
        if fixed_sql:
            is_safe2, _ = _is_safe_sql(fixed_sql)
            if is_safe2:
                try:
                    rows = run_query(fixed_sql)
                    sql  = fixed_sql
                except Exception as e2:
                    return {"answer": f"Could not execute the query after correction: {e2}", "sql": fixed_sql, "rows": [], "error": str(e2)}
            else:
                return {"answer": "Query blocked after correction attempt.", "sql": fixed_sql, "rows": [], "error": "unsafe"}
        else:
            return {"answer": f"Could not generate valid SQL. Original error: {e}", "sql": sql, "rows": [], "error": str(e)}

    # Pass 2: narrate results
    if not rows:
        narration = "No matching records were found in the dataset for this query."
    else:
        pass2_messages = [
            {"role": "system", "content": NARRATION_PROMPT},
            {"role": "user",   "content": (
                f"Question: {question}\n\n"
                f"SQL: {sql}\n\n"
                f"Results ({len(rows)} rows):\n{rows[:30]}"
            )},
        ]
        narration = _llm(pass2_messages, max_tokens=300)

    # Trim rows to the LIMIT declared in SQL — prevents over-highlighting
    limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
    display_limit = int(limit_match.group(1)) if limit_match else 100
    trimmed_rows = rows[:display_limit]

    return {"answer": narration, "sql": sql, "rows": trimmed_rows, "error": None}