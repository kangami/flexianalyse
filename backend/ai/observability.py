"""
Observability helpers — LangSmith tracing for the search agent.

LangGraph nodes are auto-traced by LangChain when LANGSMITH_TRACING is enabled
(no code needed). This module additionally wraps the raw OpenAI clients used
inside the nodes so their LLM/embedding calls show up as nested spans (prompt,
tokens, response) under each node.

Tracing is OFF unless `LANGSMITH_TRACING=true` (or the legacy
`LANGCHAIN_TRACING_V2=true`) — so production stays untraced by default, which
also keeps sensitive document content off the LangSmith SaaS.
"""
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


def tracing_enabled() -> bool:
    """True when LangSmith tracing is explicitly turned on via env."""
    return (
        os.getenv("LANGSMITH_TRACING", "").lower() in ("1", "true", "yes")
        or os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("1", "true", "yes")
    )


def make_openai_client() -> OpenAI:
    """Return an OpenAI client, wrapped for LangSmith when tracing is enabled.

    Falls back to a plain client if tracing is off or `langsmith` is missing —
    so the app keeps working with or without the dependency.
    """
    client = OpenAI()
    if not tracing_enabled():
        return client
    try:
        from langsmith.wrappers import wrap_openai
        return wrap_openai(client)
    except Exception as e:  # pragma: no cover - optional dependency
        logger.warning(
            "LangSmith tracing requested but wrap_openai unavailable (%s) — "
            "OpenAI calls won't be traced (node spans still are).", e
        )
        return client


_client = None


def get_openai_client() -> OpenAI:
    """Lazy shared OpenAI client.

    Building the client at import time (module-level `make_openai_client()`) meant
    a missing OPENAI_API_KEY blew up the whole import chain — e.g. creating a
    connector, which merely imports the ingestion tasks, failed at import. Resolve
    it on first use instead, so a config error surfaces on the call that needs
    OpenAI, not on unrelated imports.
    """
    global _client
    if _client is None:
        _client = make_openai_client()
    return _client
