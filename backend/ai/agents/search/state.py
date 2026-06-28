# backend/ai/agents/search/state.py
from typing import TypedDict, Optional


class SearchState(TypedDict):
    # ── Input
    query: str
    org_id: str
    user_role: str
    allowed_connectors: list[str]

    # ── Query understanding
    intent: str                  # 'factual' | 'analytical' | 'exploratory'
    entities: list[dict]         # [{name, type}]
    sub_queries: list[str]       # decomposed sub-queries
    needs_database: bool         # query targets the live SQL database (text-to-SQL)

    # ── Retrieval
    kg_nodes: list[dict]         # KG semantic search results
    chunks: list[dict]           # vector + FTS search results
    reranked_chunks: list[dict]  # after fusion + rerank

    # ── Live SQL (text-to-SQL on the org's connected database)
    generated_sql: str           # SELECT generated from natural language
    sql_columns: list[str]       # column names of the result set
    sql_rows: list[dict]         # rows returned by the live query
    sql_error: Optional[str]     # error message if the SQL step failed

    # ── Generation 
    context: str                 # assembled context for LLM
    answer: str                  # generated answer
    sources: list[dict]          # cited sources {title, type, connector}
    confidence: float            # 0.0 - 1.0
    grounded: bool               # grounding validation result

    # ── Control 
    retry_count: int
    error: Optional[str]