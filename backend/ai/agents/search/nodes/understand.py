# backend/ai/agents/search/nodes/understand.py
"""
Query Understanding Node
- Classifies intent
- Extracts named entities
- Decomposes complex queries into sub-queries
"""
import json
import logging

from ai.agents.search.state import SearchState
from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a search query analyst for an enterprise AI assistant.

Analyze the user query and return a JSON object with:
{
  "intent": "factual" | "analytical" | "exploratory",
  "entities": [{"name": "...", "type": "person|company|project|table|document|concept"}],
  "sub_queries": ["...", "..."],
  "needs_database": true | false
}

Intent types:
- factual: looking for a specific fact ("who is X", "what is the value of Y")
- analytical: needs aggregation or reasoning ("summarize", "compare", "how many")
- exploratory: broad discovery ("what do we have about X", "show me everything related to Y")

Sub-queries: decompose complex queries into 1-3 simpler atomic searches.
For simple queries, sub_queries = [original_query].

needs_database: set true when the query asks for structured/tabular data that
would live in a business database — counts, totals, aggregations, rankings,
filtering of records, or LISTING the entries of a table (e.g. "how many clients",
"total sales in 2025", "top 10 products by revenue", "list the departments").
If a list of "Available database tables" is provided below and the query refers
to data that would live in one of those tables — EVEN IF the wording differs in
spelling, plural/singular form, or language (e.g. "departement" → "departments",
"rôles" → "roles") — set needs_database=true. Set false only for questions truly
answered by documents, files or general knowledge.

Return ONLY the JSON object, no other text."""


def _org_sql_tables(org_id: str) -> list[str]:
    """SQL table names known for this org (local lookup) — given to the LLM so it
    can reliably decide `needs_database` despite spelling/plural/language."""
    try:
        from models.resource import Resource
        rows = Resource.query.filter(
            Resource.organization_id == org_id,
            Resource.type.in_(("sql", "sql_table")),
            Resource.deleted_at.is_(None),
        ).all()
        return [r.title for r in rows if r.title]
    except Exception as e:
        logger.warning("Could not load SQL tables for understanding: %s", e)
        return []


def understand_query(state: SearchState) -> SearchState:
    """Classify intent, extract entities, decompose query."""
    logger.info(f"Understanding query: {state['query']}")

    user_content = state["query"]
    tables = _org_sql_tables(state.get("org_id"))
    if tables:
        user_content += "\n\nAvailable database tables: " + ", ".join(tables)

    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=800,
        )

        data = json.loads(response.choices[0].message.content)

        return {
            **state,
            "intent": data.get("intent", "factual"),
            "entities": data.get("entities", []),
            "sub_queries": data.get("sub_queries", [state["query"]]),
            "needs_database": bool(data.get("needs_database", False)),
        }

    except Exception as e:
        logger.error(f"Query understanding failed: {e}")
        return {
            **state,
            "intent": "factual",
            "entities": [],
            "sub_queries": [state["query"]],
            "needs_database": False,
            "error": str(e),
        }