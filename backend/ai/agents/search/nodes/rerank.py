# backend/ai/agents/search/nodes/rerank.py
"""
Reranking Node
- Reciprocal Rank Fusion (RRF) to merge vector + FTS scores
- OpenAI cross-encoder reranking for top-N candidates
"""
import json
import logging

from ai.agents.search.state import SearchState
from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

RRF_K         = 60    # RRF constant
TOP_N_RERANK  = 20    # candidates sent to cross-encoder
FINAL_TOP_K   = 5     # final chunks kept for context


def rerank(state: SearchState) -> SearchState:
    """Fuse scores with RRF then rerank with OpenAI cross-encoder."""
    chunks = state.get("chunks", [])

    if not chunks:
        return {**state, "reranked_chunks": []}

    # Step 1 — RRF fusion
    fused = _reciprocal_rank_fusion(chunks)

    # Step 2 — OpenAI cross-encoder rerank on top-N
    candidates = fused[:TOP_N_RERANK]
    reranked   = _openai_rerank(state["query"], candidates)

    logger.info(
        f"Reranked {len(chunks)} chunks → top {len(reranked)} kept"
    )

    return {**state, "reranked_chunks": reranked[:FINAL_TOP_K]}


# ─────────────────────────────────────────────────────────────────────────────

def _reciprocal_rank_fusion(chunks: list[dict]) -> list[dict]:
    """
    Merge vector and FTS results using Reciprocal Rank Fusion.
    RRF score = sum(1 / (k + rank)) across all result lists.
    """
    # Separate by source
    vector_chunks = sorted(
        [c for c in chunks if c["source"] == "vector"],
        key=lambda x: x["score"], reverse=True
    )
    fts_chunks = sorted(
        [c for c in chunks if c["source"] == "fts"],
        key=lambda x: x["score"], reverse=True
    )

    # Compute RRF scores
    rrf_scores: dict[str, float] = {}
    chunk_map:  dict[str, dict]  = {}

    for rank, chunk in enumerate(vector_chunks):
        cid = chunk["id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + rank + 1)
        chunk_map[cid]  = chunk

    for rank, chunk in enumerate(fts_chunks):
        cid = chunk["id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + rank + 1)
        chunk_map[cid]  = chunk

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
    return [
        {**chunk_map[cid], "rrf_score": rrf_scores[cid]}
        for cid in sorted_ids
    ]


def _openai_rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    Cross-encoder reranking using GPT-4o-mini.
    Scores each candidate's relevance to the query (0-10).
    """
    if not candidates:
        return []

    # Build candidates list for the prompt
    candidates_text = "\n\n".join(
        f"[{i}] Source: {c.get('resource_title', 'unknown')} "
        f"({c.get('connector_type', '')})\n{c['content'][:300]}"
        for i, c in enumerate(candidates)
    )

    prompt = f"""Query: {query}

Rate each passage's relevance to the query on a scale 0-10.
Return ONLY a JSON array of scores in the same order as the passages.
Example: [8, 3, 10, 1, 7]

Passages:
{candidates_text}"""

    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a relevance scoring engine. "
                        "Return a JSON object with key 'scores' "
                        "containing an array of integers 0-10."
                    )
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
        )

        data    = json.loads(response.choices[0].message.content)
        scores  = data.get("scores", [])

        # Attach scores and sort
        scored = []
        for i, chunk in enumerate(candidates):
            score = scores[i] if i < len(scores) else 0
            scored.append({**chunk, "rerank_score": score})

        return sorted(scored, key=lambda x: x["rerank_score"], reverse=True)

    except Exception as e:
        logger.error(f"OpenAI rerank failed: {e} — falling back to RRF order")
        return candidates