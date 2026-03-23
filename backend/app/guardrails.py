"""
Guardrails: restrict the chat interface to SAP O2C dataset questions only.
Uses a two-layer check: keyword allowlist + off-topic blocklist.
"""

import re

DOMAIN_KEYWORDS = {
    # core O2C entities
    "order", "sales order", "delivery", "invoice", "billing", "payment",
    "billing document", "journal", "journal entry", "gl account",
    # SAP-specific
    "material", "plant", "storage", "profit center", "cost center",
    "company code", "fiscal year", "accounting document",
    # business entities
    "customer", "product", "partner", "business partner", "address",
    "schedule line", "distribution channel", "sales organization",
    # analysis words tied to dataset
    "flow", "trace", "broken", "incomplete", "undelivered", "unbilled",
    "reconcile", "outstanding", "revenue", "quantity", "amount", "net amount",
    "cancelled", "cancellation", "incoterms", "payment terms",
    # table names (in case user types them)
    "outbound", "receivable", "erp", "sap", "o2c",
}

OFF_TOPIC_PATTERNS = [
    r"\bpoem\b", r"\bstory\b", r"\bjoke\b", r"\bwrite me\b",
    r"\brecipe\b", r"\bweather\b", r"\bsport\b",
    r"\bwho is\b", r"\bwhat is [a-z]+ (the )?(capital|president|prime minister)\b",
    r"\bhow to cook\b", r"\btranslate\b", r"\bcode for\b", r"\bpython code\b",
    r"\bjavascript\b", r"\bhtml\b", r"\bexplain (quantum|relativity|gravity)\b",
    r"\b(2\s*\+\s*2|math problem)\b",
    r"\bgeneral knowledge\b", r"\bwikipedia\b",
    # social / emotional
    r"\bhow are you\b", r"\bwhat is your name\b", r"\bwho made you\b",
    r"\bthank you\b", r"\bhello\b", r"^hi$", r"^hey$", r"^hello$",
]

# Vague unbounded queries — let through but LLM will redirect to specific table
VAGUE_PATTERNS = [
    r"^show me all( data)?$",
    r"^(give|show|list|display) (me )?(all|everything|all records|all data)$",
    r"^(everything|all of it|all records)$",
]

REJECTION_MSG = (
    "This system is designed to answer questions related to the provided "
    "SAP O2C dataset only. Please ask about sales orders, deliveries, "
    "billing documents, payments, products, customers, or plants."
)


def is_domain_query(question: str) -> bool:
    """Return True if question is plausibly about the O2C dataset."""
    q = question.lower().strip()

    # Hard block: explicit off-topic patterns
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, q):
            return False

    # Pass: contains at least one domain keyword
    for kw in DOMAIN_KEYWORDS:
        if kw in q:
            return True

    # Short queries that are ambiguous — allow through, LLM will reject if needed
    word_count = len(q.split())
    if word_count <= 5:
        return True

    # Fall back: reject — LLM guardrail is the second line of defence
    return False