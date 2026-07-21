# backend/ai/agents/search/nodes/generate.py
"""
Answer Generation + Grounding Validation Node
- Assembles context from KG nodes + reranked chunks
- Generates grounded answer with GPT-4o
- Validates answer is supported by sources
"""
import json
import logging

from ai.agents.search.state import SearchState
from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 12000

_LANG_NAMES = {
    "en": "English", "fr": "French", "es": "Spanish", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "ar": "Arabic", "zh": "Chinese", "ja": "Japanese", "tr": "Turkish",
}


def _detect_language_name(text: str) -> str | None:
    """Human-readable language name of the text (e.g. 'English'), or None.

    The retrieved documents are often in French, which biases the model to
    answer in French even for English questions — so we detect the QUERY language
    explicitly and force the answer into it."""
    if not text or len(text.strip()) < 4:
        return None
    try:
        from langdetect import detect
        return _LANG_NAMES.get(detect(text)[:2])
    except Exception:
        return None


def assemble_context(state: SearchState) -> SearchState:
    """Build the context string for the answer.

    SQL-first: when the live SQL query returned rows, that result is the answer —
    we deliberately IGNORE the KG nodes and document chunks (and their sources).
    Blending document search into a database answer is what made the model
    contradict a correct SQL result and cite chunks from another connector.
    Document context is used only as a fallback when SQL produced nothing.
    """
    parts   = []
    sources = []

    sql_rows = state.get("sql_rows", [])
    has_sql  = bool(sql_rows)

    # KG context — structural information (skipped when SQL answered)
    kg_nodes = state.get("kg_nodes", [])
    if kg_nodes and not has_sql:
        parts.append("## Structural Context (Knowledge Graph)")
        for node in kg_nodes[:5]:
            parts.append(
                f"- [{node['type'].upper()}] {node['name']}"
                + (f" (via {node['connector']})" if node.get('connector') else "")
            )

    # Chunk context — actual content (skipped when SQL answered)
    reranked = state.get("reranked_chunks", [])
    if reranked and not has_sql:
        parts.append("\n## Document/Data Content")
        for chunk in reranked:
            title    = chunk.get("resource_title", "Unknown")
            ctype    = chunk.get("connector_type", "")
            score    = chunk.get("rerank_score", 0)
            section  = chunk.get("section_title", "")
            page     = chunk.get("page_number")

            header = f"### {title}"
            if section:
                header += f" › {section}"
            if page:
                header += f" (page {page})"
            header += f" [{ctype}] (relevance: {score}/10)"

            parts.append(header)
            parts.append(chunk["content"])
            parts.append("---")

            sources.append({
                "title":     title,
                "type":      chunk.get("chunk_type"),
                "connector": ctype,
                "score":     score,
            })

    # Live SQL context — authoritative tabular data from the org's database
    if sql_rows:
        parts.append("\n## Live Database Query Result")
        generated_sql = state.get("generated_sql", "")
        if generated_sql:
            parts.append(f"Query: `{generated_sql}`")
        if state.get("sql_uncertain"):
            # The ReAct reviewer could not confirm this query — tell the model to
            # answer with the data but explicitly flag the uncertainty.
            parts.append(
                "NOTE: this query could not be fully validated. Report the figures "
                "but clearly warn the user that the result may be unreliable."
            )
        parts.append(_format_sql_rows(state.get("sql_columns", []), sql_rows))

        sources.append({
            "title":     "Live SQL query",
            "type":      "sql",
            "connector": "sql",
            "score":     10,
        })
    elif state.get("sql_error") and (state.get("needs_database") or state.get("generated_sql")):
        parts.append(
            f"\n## Live Database Query\n(No data returned — {state['sql_error']})"
        )

    context = "\n".join(parts)

    # Truncate if too long
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n...[truncated]"

    return {**state, "context": context, "sources": sources}


def _format_sql_rows(columns: list, rows: list[dict], max_rows: int = 50) -> str:
    """Render SQL rows as a compact markdown table for the LLM context."""
    if not rows:
        return "(no rows)"

    cols = columns or list(rows[0].keys())
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep    = "| " + " | ".join("---" for _ in cols) + " |"
    body   = [
        "| " + " | ".join(str(row.get(c, "")) for c in cols) + " |"
        for row in rows[:max_rows]
    ]
    table = "\n".join([header, sep, *body])
    if len(rows) > max_rows:
        table += f"\n...({len(rows) - max_rows} more rows)"
    return table


def _answer_messages(state: SearchState):
    """Build the (system, user) chat messages for the answer.

    Returns (messages, ""). On empty context returns (None, fallback) so callers
    use the fallback string without an LLM call. Shared by generate_answer
    (non-stream) and stream_answer_tokens (SSE).
    """
    query   = state["query"]
    context = state.get("context", "")
    intent  = state.get("intent", "factual")

    lang_name = _detect_language_name(query)

    if not context.strip():
        return None, (
            "Je n'ai trouvé aucune information pertinente pour votre requête."
            if lang_name == "French"
            else "I couldn't find any relevant information for your query."
        )

    lang_line = (
        f"You MUST write your ENTIRE answer in {lang_name}, regardless of the "
        f"language of the documents in the context."
        if lang_name else
        "You MUST write your ENTIRE answer in the SAME language as the user's "
        "question, regardless of the language of the documents in the context."
    )

    system_prompt = f"""You are an enterprise search assistant with access to the organization's documents, databases, and files.

Your task: answer the user's query using ONLY the provided context.

{lang_line}

Rules:
1. Base your answer EXCLUSIVELY on the context provided — never hallucinate
2. Cite your sources using [Source: title] notation
3. If the context doesn't contain enough information, say so explicitly
4. For {intent} queries: {"provide a direct, specific answer" if intent == "factual" else "provide analysis with supporting evidence" if intent == "analytical" else "provide a comprehensive overview"}
5. Be concise but complete
6. If a "Live Database Query Result" table is present, treat it as authoritative
   structured data: report exact figures from it and summarize the rows clearly
7. SUBJECT MATCH IS MANDATORY. Identify the exact subject of the query (the
   specific person, entity, file or topic named). Use ONLY context that is about
   THAT subject. If the context is about a DIFFERENT subject (e.g. another
   person's payslip), DO NOT use it, DO NOT report its figures, and DO NOT
   describe it as a partial match — it is simply not an answer.
8. Answer ONLY the current question, on its own. Never refer to a previous
   question, a previous answer, or any other subject the user did not ask about.

If the context contains nothing about the requested subject, say briefly that no
information was found for that subject — written in the answer language — and
nothing else."""

    user = (
        f"Context:\n{context}\n\nQuery: {query}\n\n"
        f"(Answer in {lang_name or 'the same language as the question'}.)"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ], ""


def generate_answer(state: SearchState) -> SearchState:
    """Generate a grounded answer (non-streaming)."""
    messages, fallback = _answer_messages(state)
    if messages is None:
        return {**state, "answer": fallback, "confidence": 0.0, "grounded": True}
    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini", messages=messages, max_tokens=2000,
        )
        return {
            **state,
            "answer":     response.choices[0].message.content,
            "confidence": 0.9,
            "grounded":   False,
        }
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return {
            **state,
            "answer":     f"Search failed: {str(e)}",
            "confidence": 0.0,
            "grounded":   True,
            "error":      str(e),
        }


def stream_answer_tokens(state: SearchState):
    """Yield the answer as text deltas (for SSE). Same prompt as generate_answer."""
    messages, fallback = _answer_messages(state)
    if messages is None:
        yield fallback
        return
    try:
        stream = get_openai_client().chat.completions.create(
            model="gpt-4o-mini", messages=messages, max_tokens=2000, stream=True,
        )
        for chunk in stream:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = getattr(choices[0].delta, "content", None)
            if delta:
                yield delta
    except Exception as e:
        logger.error(f"Answer streaming failed: {e}")
        yield f"Search failed: {str(e)}"


def validate_answer(state: SearchState) -> SearchState:
    """
    Grounding check — verify the answer is supported by the context.
    Returns grounded=True/False and updated confidence score.
    """
    answer  = state.get("answer", "")
    context = state.get("context", "")
    chunks  = state.get("reranked_chunks", [])

    # Live SQL rows are authoritative ground truth — skip the LLM grounding check
    # (faster, and avoids false "not grounded" retries caused by document noise).
    if state.get("sql_rows"):
        return {**state, "grounded": True, "confidence": 1.0}

    # If no chunks found → honest "no results" answer is always grounded
    if not chunks:
        return {**state, "grounded": True, "confidence": 1.0}

    # Quick heuristic — if answer mentions "couldn't find" it's grounded
    if any(phrase in answer.lower() for phrase in [
        "couldn't find", "no information", "not available",
        "insufficient", "based on available data",
        "aucune information", "rien trouvé", "pas trouvé", "aucune donnée",
    ]):
        return {**state, "grounded": True, "confidence": 0.7}

    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a fact-checker. Verify if the answer is "
                        "fully supported by the context. "
                        "Return JSON: {\"grounded\": true/false, \"confidence\": 0.0-1.0, "
                        "\"reason\": \"brief explanation\"}"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context[:3000]}\n\n"
                        f"Answer to verify:\n{answer[:1000]}"
                    )
                },
            ],
            temperature=0,
            max_tokens=200,
        )

        data       = json.loads(response.choices[0].message.content)
        grounded   = data.get("grounded", False)
        confidence = float(data.get("confidence", 0.5))

        logger.info(
            f"Grounding check: grounded={grounded} "
            f"confidence={confidence} reason={data.get('reason')}"
        )

        return {**state, "grounded": grounded, "confidence": confidence}

    except Exception as e:
        logger.error(f"Grounding validation failed: {e}")
        return {**state, "grounded": True, "confidence": 0.5}