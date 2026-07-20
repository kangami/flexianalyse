# backend/ai/agents/search/nodes/retrieve.py
"""
Hybrid Retrieval Node
- KG semantic search (structure + entities)
- Vector search on resource_chunks (pgvector)
- PostgreSQL Full-Text Search (exact matches)
"""
import logging
import os
from uuid import UUID

from sqlalchemy import text
from config.extensions import db
from ai.agents.search.state import SearchState
from ai.ingestion.embedder import Embedder
from ai.knowledge.knowledge_graph_builder import KnowledgeGraphBuilder

logger = logging.getLogger(__name__)
_embedder = Embedder()

# Max results per retrieval method
KG_LIMIT      = 10
VECTOR_LIMIT  = 20
FTS_LIMIT     = 10
EMBEDDING_DIM = 1536

# Full-text search language: chosen dynamically per query so a multilingual
# client base works. Set FTS_LANGUAGE to force one Postgres regconfig.
FTS_LANGUAGE_OVERRIDE = os.getenv("FTS_LANGUAGE")  # e.g. "french" to force
FTS_MIN_CHARS_FOR_DETECT = 12  # below this, detection is unreliable → 'simple'

# ISO 639-1 → Postgres text-search config (only langs Postgres ships by default).
_PG_TS_CONFIGS = {
    "fr": "french", "en": "english", "es": "spanish", "de": "german",
    "it": "italian", "pt": "portuguese", "nl": "dutch", "ru": "russian",
    "sv": "swedish", "no": "norwegian", "da": "danish", "fi": "finnish",
    "tr": "turkish", "hu": "hungarian", "ro": "romanian",
}


def _fts_regconfig(query: str) -> str:
    """Pick a Postgres text-search config for this query.

    'simple' (no stemming, language-agnostic) is the safe fallback — it still
    matches exact tokens (names, numbers, codes) in ANY language, and the dense
    vector leg covers morphology/semantics.
    """
    if FTS_LANGUAGE_OVERRIDE:
        return FTS_LANGUAGE_OVERRIDE
    if not query or len(query.strip()) < FTS_MIN_CHARS_FOR_DETECT:
        return "simple"
    try:
        from langdetect import detect
        return _PG_TS_CONFIGS.get(detect(query)[:2], "simple")
    except Exception:
        return "simple"


def retrieve(state: SearchState) -> SearchState:
    """Run all retrieval methods in parallel and combine results."""
    # Pure database question → skip document retrieval entirely (the embedding
    # call + KG/vector/FTS searches). The live SQL node answers it, so doc search
    # over ingested chunks only adds latency. rerank then no-ops on empty chunks.
    if state.get("needs_database"):
        logger.info("Retrieve skipped — query targets the database")
        return {**state, "kg_nodes": [], "chunks": []}

    org_id = state["org_id"]
    sub_queries = state.get("sub_queries") or [state["query"]]
    allowed = set(state.get("allowed_connectors") or
                  ["sql", "google_drive", "dropbox", "sharepoint"])

    kg_nodes: list[dict] = []
    chunks:   list[dict] = []

    for sub_query in sub_queries:
        # Embed the sub-query ONCE and reuse it for both vector and KG search
        # (previously embedded twice per sub-query — wasted an API round-trip).
        embedding = _embedder.embed_single(sub_query)

        # 1 — KG search
        kg_nodes.extend(_search_kg(org_id, sub_query, allowed, embedding))

        # 2 — Vector search
        chunks.extend(_search_vector(org_id, allowed, embedding))

        # 3 — Full-Text Search
        chunks.extend(_search_fts(org_id, sub_query, allowed))

    # Deduplicate by id
    seen_kg   = set()
    seen_ch   = set()
    kg_nodes  = [n for n in kg_nodes
                 if not (str(n["id"]) in seen_kg or seen_kg.add(str(n["id"])))]
    chunks    = [c for c in chunks
                 if not (str(c["id"]) in seen_ch or seen_ch.add(str(c["id"])))]

    logger.info(
        f"Retrieved {len(kg_nodes)} KG nodes and {len(chunks)} chunks "
        f"for {len(sub_queries)} sub-queries"
    )

    return {**state, "kg_nodes": kg_nodes, "chunks": chunks}


# ─────────────────────────────────────────────────────────────────────────────

def _search_kg(org_id: str, query: str, allowed: set, embedding: list = None) -> list[dict]:
    """Semantic search on KG nodes."""
    try:
        builder = KnowledgeGraphBuilder(org_id)
        nodes = builder.semantic_search(query, limit=KG_LIMIT, embedding=embedding)
        return [
            {
                "id": str(n.id),
                "name": n.name,
                "type": n.node_type,
                "connector": n.connector_type,
                "metadata": n.kgnode_metadata,
                "source": "kg",
                "score": 1.0,  # pgvector distance not exposed directly
            }
            for n in nodes
            if not n.connector_type or n.connector_type in allowed
        ]
    except Exception as e:
        logger.error(f"KG search failed: {e}")
        return []


def _search_vector(org_id: str, allowed: set, embedding: list = None) -> list[dict]:
    """pgvector cosine similarity search on resource_chunks."""
    try:
        if not embedding:
            return []

        rows = db.session.execute(
            text("""
                SELECT
                    rc.id,
                    rc.content,
                    rc.chunk_type,
                    rc.section_title,
                    rc.page_number,
                    r.title        AS resource_title,
                    r.type         AS connector_type,
                    r.external_id  AS external_id,
                    1 - (rc.embedding <=> CAST(:embedding AS vector)) AS score
                FROM resource_chunks rc
                JOIN resources r ON r.id = rc.resource_id
                WHERE rc.organization_id = :org_id
                  AND r.deleted_at IS NULL
                  AND rc.embedding IS NOT NULL
                ORDER BY rc.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            {
                "org_id": org_id,
                "embedding": str(embedding),
                "limit": VECTOR_LIMIT,
            },
        ).fetchall()

        return [
            {
                "id": str(row.id),
                "content": row.content,
                "chunk_type": row.chunk_type,
                "section_title": row.section_title,
                "page_number": row.page_number,
                "resource_title": row.resource_title,
                "connector_type": row.connector_type,
                "external_id": row.external_id,
                "source": "vector",
                "score": float(row.score),
            }
            for row in rows
            if not row.connector_type or row.connector_type in allowed
        ]
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


def _search_fts(org_id: str, query: str, allowed: set) -> list[dict]:
    """PostgreSQL full-text search on resource_chunks content.

    Uses `websearch_to_tsquery` (tolerant of any user input — no manual term
    sanitization, handles phrases/accents/apostrophes and never raises on
    syntax) with a language-aware config so French content stems correctly.
    """
    try:
        if not query or not query.strip():
            return []

        lang = _fts_regconfig(query)

        rows = db.session.execute(
            text("""
                SELECT
                    rc.id,
                    rc.content,
                    rc.chunk_type,
                    rc.section_title,
                    rc.page_number,
                    r.title        AS resource_title,
                    r.type         AS connector_type,
                    r.external_id  AS external_id,
                    ts_rank(
                        to_tsvector(CAST(:lang AS regconfig), rc.content),
                        websearch_to_tsquery(CAST(:lang AS regconfig), :q)
                    ) AS score
                FROM resource_chunks rc
                JOIN resources r ON r.id = rc.resource_id
                WHERE rc.organization_id = :org_id
                  AND r.deleted_at IS NULL
                  AND to_tsvector(CAST(:lang AS regconfig), rc.content)
                      @@ websearch_to_tsquery(CAST(:lang AS regconfig), :q)
                ORDER BY score DESC
                LIMIT :limit
            """),
            {"org_id": org_id, "q": query, "lang": lang, "limit": FTS_LIMIT},
        ).fetchall()

        return [
            {
                "id": str(row.id),
                "content": row.content,
                "chunk_type": row.chunk_type,
                "section_title": row.section_title,
                "page_number": row.page_number,
                "resource_title": row.resource_title,
                "connector_type": row.connector_type,
                "external_id": row.external_id,
                "source": "fts",
                "score": float(row.score),
            }
            for row in rows
            if not row.connector_type or row.connector_type in allowed
        ]
    except Exception as e:
        logger.error(f"FTS search failed: {e}")
        return []