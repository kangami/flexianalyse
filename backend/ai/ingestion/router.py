"""
Adaptive Ingestion Router
=========================
Decides the best ingestion *strategy* for each document, based on its type:

  - financial / tabular / charts  → "layout_table"        (focus on structure)
  - research paper / prose        → "semantic"            (focus on meaning)
  - legal contract                → "legal_hierarchical"  (focus on hierarchy + metadata)
  - anything else                 → "generic"             (current behaviour)

Cheap deterministic signals (format, filename) are tried first; an LLM classifier
runs only when needed, on a SAMPLE of the document (not the whole thing). On any
failure it falls back to "generic" — so routing never breaks ingestion.

NOTE (phase 1/2): all strategies currently execute the generic extraction path;
the per-strategy extractors are wired in next. The decision is already recorded
on each resource so we get visibility (and metadata) immediately.
"""
import json
import logging
import os
from dataclasses import dataclass

from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

ROUTER_MODEL = os.getenv("INGESTION_ROUTER_MODEL", "gpt-4o-mini")
ROUTER_LLM_ENABLED = os.getenv("INGESTION_ROUTER_LLM", "true").lower() in ("1", "true", "yes")

# doc_type → ingestion strategy
_STRATEGY_BY_TYPE = {
    "financial": "layout_table",
    "research":  "semantic",
    "legal":     "legal_hierarchical",
    "generic":   "generic",
}


@dataclass
class RouteDecision:
    doc_type: str
    strategy: str
    confidence: float
    reason: str


def _decision(doc_type: str, confidence: float = 1.0, reason: str = "") -> RouteDecision:
    dt = doc_type if doc_type in _STRATEGY_BY_TYPE else "generic"
    return RouteDecision(dt, _STRATEGY_BY_TYPE[dt], confidence, reason)


def classify_document(file_format: str, filename: str, sample_text: str = "") -> RouteDecision:
    """Return the routing decision for a document."""
    fmt = (file_format or "").lower()

    # Deterministic fast-paths — no LLM needed.
    if fmt in ("csv", "xlsx", "sheet"):
        return _decision("financial", 1.0, "spreadsheet / tabular format")
    if fmt in ("text",):
        return _decision("generic", 1.0, "plain text / code")

    if not ROUTER_LLM_ENABLED:
        return _decision("generic", 0.5, "router LLM disabled")

    try:
        decision = _classify_llm(filename, sample_text)
        logger.info(
            "Router: %s → %s (%.0f%%) — %s",
            filename, decision.strategy, decision.confidence * 100, decision.reason,
        )
        return decision
    except Exception as e:
        logger.warning("Router LLM failed for %s (%s) — using generic", filename, e)
        return _decision("generic", 0.0, f"router error: {e}")


def _classify_llm(filename: str, sample_text: str) -> RouteDecision:
    prompt = f"""Classify this document into ONE type to choose its ingestion strategy.

Filename: {filename}
Sample (start of the document, may be empty):
\"\"\"{(sample_text or '')[:3000]}\"\"\"

Types:
- financial: financial report, invoice, payslip/bulletin de paie, accounting,
  budget — anything table/number-heavy or with charts.
- research: research paper, article, study, mostly explanatory prose.
- legal: contract, agreement, terms, lease, anything with legal clauses /
  articles / sections / parties.
- generic: anything else.

Return JSON exactly: {{"doc_type":"financial|research|legal|generic","confidence":0.0-1.0,"reason":"short"}}"""

    resp = get_openai_client().chat.completions.create(
        model=ROUTER_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a document classifier. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=150,
    )
    data = json.loads(resp.choices[0].message.content)
    return _decision(
        data.get("doc_type", "generic"),
        float(data.get("confidence", 0.5)),
        data.get("reason", ""),
    )
