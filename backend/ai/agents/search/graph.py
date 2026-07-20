# backend/ai/agents/search/graph.py
"""
Search Agent — LangGraph definition
"""
import logging
from langgraph.graph import StateGraph, END

from ai.agents.search.state import SearchState
from ai.agents.search.nodes.understand import understand_query
from ai.agents.search.nodes.retrieve import retrieve
from ai.agents.search.nodes.rerank import rerank
from ai.agents.search.nodes.sql_query import sql_query
from ai.agents.search.nodes.generate import assemble_context, generate_answer, validate_answer

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _should_retry(state: SearchState) -> str:
    """Route after validation — retry if not grounded and under retry limit."""
    if state.get("grounded"):
        return "end"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        logger.warning("Max retries reached — returning best effort answer")
        return "end"
    return "retry"


def _reformulate(state: SearchState) -> SearchState:
    """Reformulate query on retry — add more context from entities."""
    entities = state.get("entities", [])
    entity_names = " ".join(e["name"] for e in entities[:3])
    new_query = f"{state['query']} {entity_names}".strip()

    logger.info(
        f"Reformulating query (retry {state.get('retry_count', 0) + 1}): "
        f"{state['query']} → {new_query}"
    )

    return {
        **state,
        "query":       new_query,
        "retry_count": state.get("retry_count", 0) + 1,
        "chunks":      [],
        "kg_nodes":    [],
        "reranked_chunks": [],
    }


def build_search_graph() -> StateGraph:
    """Build and compile the Search Agent graph."""
    graph = StateGraph(SearchState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    graph.add_node("understand_query",  understand_query)
    graph.add_node("retrieve",          retrieve)
    graph.add_node("rerank",            rerank)
    graph.add_node("sql_query",         sql_query)
    graph.add_node("assemble_context",  assemble_context)
    graph.add_node("generate_answer",   generate_answer)
    graph.add_node("validate_answer",   validate_answer)
    graph.add_node("reformulate_query", _reformulate)

    # ── Edges ──────────────────────────────────────────────────────────────
    graph.set_entry_point("understand_query")
    graph.add_edge("understand_query",  "retrieve")
    graph.add_edge("retrieve",          "rerank")
    graph.add_edge("rerank",            "sql_query")
    graph.add_edge("sql_query",         "assemble_context")
    graph.add_edge("assemble_context",  "generate_answer")
    graph.add_edge("generate_answer",   "validate_answer")
    graph.add_edge("reformulate_query", "retrieve")  # retry loop

    graph.add_conditional_edges(
        "validate_answer",
        _should_retry,
        {"end": END, "retry": "reformulate_query"},
    )

    return graph.compile()


# Singleton — compiled once
search_agent = build_search_graph()


def run_search(
    query: str,
    org_id: str,
    user_role: str = "employee",
    allowed_connectors: list[str] = None,
    scope_connector_id: str = None,
) -> dict:
    """
    Run the search agent and return the result.
    Entry point for Flask endpoints and other agents.
    `scope_connector_id` limits the live SQL to one connector (search perimeter).
    """
    initial_state: SearchState = {
        "query":               query,
        "org_id":              org_id,
        "user_role":           user_role,
        "allowed_connectors":  allowed_connectors or ["sql", "google_drive", "dropbox"],
        "scope_connector_id":  scope_connector_id,
        "intent":              "",
        "entities":            [],
        "sub_queries":         [],
        "needs_database":      False,
        "kg_nodes":            [],
        "chunks":              [],
        "reranked_chunks":     [],
        "generated_sql":       "",
        "sql_columns":         [],
        "sql_rows":            [],
        "sql_error":           None,
        "context":             "",
        "answer":              "",
        "sources":             [],
        "confidence":          0.0,
        "grounded":            False,
        "retry_count":         0,
        "error":               None,
    }

    final_state = search_agent.invoke(initial_state)

    return {
        "answer":        final_state["answer"],
        "sources":       final_state["sources"],
        "confidence":    final_state["confidence"],
        "intent":        final_state["intent"],
        "entities":      final_state["entities"],
        "generated_sql": final_state.get("generated_sql", ""),
        "sql_error":     final_state.get("sql_error"),
        "sql_columns":   final_state.get("sql_columns", []),
        "sql_rows":      final_state.get("sql_rows", []),
    }