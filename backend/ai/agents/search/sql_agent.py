# backend/ai/agents/search/sql_agent.py
"""
SQL ReAct sub-agent — Plan → Act → Reflect (LangGraph)
======================================================
Hardens Text-to-SQL against hallucination. Instead of generating one query and
trusting it blindly, this LangGraph sub-graph:

  plan     → reason about the tables / FK join path / filters / aggregation
  generate → write the SQL (act), incorporating the plan and any prior critique
  execute  → run it via the SQL MCP server (act / observe)
  reflect  → judge whether the SQL *and its result* actually answer the question
             (reason); on a wrong or failed query, feed the critique back and
             retry — up to MAX_SQL_ATTEMPTS.

`run_sql_react()` is called from the sql_query node, so BOTH the normal graph and
the streaming path get validated results. Only a query that survives the review
(or the best effort after the retry budget, flagged `uncertain`) reaches the user.
"""
import os
import re
import json
import logging
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

# Errors that mean the SQL referenced a column/relation not in the schema — the
# signal to re-teach the model the real columns + join path from the graph.
_SCHEMA_ERR_RE = re.compile(
    r"does not exist|unknown column|no such column|invalid column|"
    r"no such table|doesn't exist|unknown table",
    re.IGNORECASE,
)


def _targets_from_text(text: str, known: list) -> list:
    """Table names from `known` that appear as whole words in `text` (the plan),
    in order of first appearance. These are the tables the query needs to connect."""
    low = (text or "").lower()
    found = []
    for name in known:
        if name and re.search(rf"(?<![\w]){re.escape(name.lower())}(?![\w])", low):
            found.append(name)
    return found


def _tables_in_sql(sql: str, known: set) -> list:
    """Known table names referenced after FROM/JOIN in the SQL (base name, no alias)."""
    out, seen = [], set()
    for m in re.finditer(r"(?is)\b(?:from|join)\s+([a-zA-Z_][\w]*)", sql or ""):
        t = m.group(1)
        if t in known and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _schema_hint_for_error(msg: str, sql: str, graph) -> str:
    """On a missing-column/relation error, hand back the real columns + FK of the
    tables the query used, plus the only valid join path between them."""
    if graph is None or not _SCHEMA_ERR_RE.search(msg or ""):
        return ""
    tables = _tables_in_sql(sql, set(graph.tables()))
    if not tables:
        return ""
    lines = [graph.table_line(t) for t in tables]
    path, _ = graph.render_join_path(tables)
    hint = ("Here is the REAL schema for the tables you used (use only these columns "
            "and foreign keys):\n" + "\n".join(lines))
    if path:
        hint += f"\nThe ONLY valid join path between them is: {path}"
    return hint

MAX_SQL_ATTEMPTS = int(os.getenv("SQL_REACT_MAX_ATTEMPTS", "3"))
PLAN_MODEL       = os.getenv("SQL_PLAN_MODEL", "gpt-4o-mini")
REFLECT_MODEL    = os.getenv("SQL_REFLECT_MODEL", "gpt-4o")
REFLECT_SAMPLE_ROWS = 20


class SqlReActState(TypedDict):
    # input
    question: str
    db_schema: str
    database_url: str
    model: str           # SQL generation model (from the org's plan tier)
    max_rows: int
    schema_graph: object  # SchemaGraph | None — FK graph for join paths / error hints
    prior_sql: str       # last validated SQL of the conversation — keeps follow-ups on the same query basis
    # working state
    plan: str
    join_paths: str      # exact FK join conditions between the tables the question needs
    sql: str
    columns: list
    rows: list
    sql_error: Optional[str]
    feedback: str        # error or critique carried into the next generation
    attempts: int
    valid: bool
    verdict_reason: str
    uncertain: bool


# ── Nodes ────────────────────────────────────────────────────────────────────

def _plan_node(state: SqlReActState) -> SqlReActState:
    """Reason about HOW to answer before writing any SQL."""
    prior_block = (
        f"\nEarlier in this conversation, this query correctly answered the previous "
        f"question:\n{state['prior_sql']}\n"
        "For CONSISTENCY, reuse the same tables, date column and measures unless the "
        "new question explicitly asks for something else.\n"
        if state.get("prior_sql") else ""
    )
    prompt = f"""Schema. Each line is `table(column type, ...)` and may end with
`[FK: col -> other_table(col)]`:
{state['db_schema']}
{prior_block}
Question: {state['question']}

Produce a SHORT plan to answer it with SQL — do NOT write SQL yet:
- FIRST, map the user's terms to the actual tables/columns. Their wording often
  differs from the schema (synonyms/domain terms): e.g. customer≈client≈renter≈buyer,
  movie≈film, product≈item. Pick the table that matches BY MEANING, even if the
  exact word isn't a table name.
- which tables, and the FK join path between them (join only along [FK: ...]);
- the exact filters (column and concrete value) implied by the question;
- the aggregation / grouping / ordering needed.
Max 5 lines."""
    try:
        resp = get_openai_client().chat.completions.create(
            model=PLAN_MODEL,
            messages=[
                {"role": "system", "content": "You plan SQL queries precisely and concisely."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=250,
            temperature=0,
        )
        plan = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("SQL plan step failed: %s", e)
        plan = ""

    # Compute the exact FK join path between the tables the plan names, straight
    # from the schema graph — so the generator follows the real route (e.g. through
    # `conversation`) instead of inventing a direct foreign key.
    graph = state.get("schema_graph")
    join_paths, schema = "", state["db_schema"]
    if graph is not None:
        targets = _targets_from_text(plan + " " + state["question"], graph.tables())
        join_paths, on_tables = graph.render_join_path(targets)
        # Make sure every table on the path is in the schema text (a bridge table
        # may have been dropped by retrieval on a large schema).
        additions = [
            graph.table_line(t) for t in on_tables
            if t and not re.search(rf"(?m)^{re.escape(t)}\(", schema)
        ]
        if additions:
            schema = schema + "\n" + "\n".join(additions)
        if join_paths:
            logger.info("SQL join path: %s", join_paths)

    return {**state, "plan": plan, "join_paths": join_paths, "db_schema": schema}


def _generate_node(state: SqlReActState) -> SqlReActState:
    """Write the SQL (act), using the plan and any critique from a prior attempt."""
    from ai.agents.search.nodes.sql_query import _generate_sql
    sql = _generate_sql(
        state["question"], state["db_schema"], state["model"],
        plan=state.get("plan", ""), feedback=state.get("feedback", ""),
        join_paths=state.get("join_paths", ""), prior_sql=state.get("prior_sql", ""),
    )
    return {**state, "sql": sql, "attempts": state.get("attempts", 0) + 1,
            "sql_error": None, "feedback": ""}


def _execute_node(state: SqlReActState) -> SqlReActState:
    """Run the SQL via the MCP server (act / observe)."""
    from ai.agents.search.nodes.sql_query import (
        _is_safe_select, _call_sql_tool, MAX_RESULT_ROWS, QUERY_EXEC_TIMEOUT,
    )
    sql = state.get("sql", "")
    if not sql:
        return {**state, "rows": [], "columns": [], "sql_error": "empty query"}
    if not _is_safe_select(sql):
        return {**state, "rows": [], "columns": [],
                "sql_error": "not a safe read-only SELECT",
                "feedback": "Your statement was not a single read-only SELECT. Return only a SELECT."}
    try:
        result = _call_sql_tool(
            "query_database",
            {"sql_query": sql, "limit": state.get("max_rows", MAX_RESULT_ROWS)},
            state["database_url"],
            timeout=QUERY_EXEC_TIMEOUT,
        )
    except Exception as e:
        hint = _schema_hint_for_error(str(e), sql, state.get("schema_graph"))
        fb = f"The query raised an error: {e}. Fix the SQL."
        return {**state, "rows": [], "columns": [], "sql_error": str(e),
                "feedback": f"{fb}\n{hint}" if hint else fb}
    if result.get("status") != "success":
        msg = result.get("message", "query execution failed")
        hint = _schema_hint_for_error(msg, sql, state.get("schema_graph"))
        fb = f"The query failed: {msg}. Fix the SQL."
        return {**state, "rows": [], "columns": [], "sql_error": msg,
                "feedback": f"{fb}\n{hint}" if hint else fb}
    return {**state, "sql_error": None,
            "columns": result.get("columns", []), "rows": result.get("rows", [])}


def _reflect_node(state: SqlReActState) -> SqlReActState:
    """Judge whether the SQL + result actually answer the question (reason)."""
    rows = state.get("rows", [])
    sample = json.dumps(rows[:REFLECT_SAMPLE_ROWS], default=str)[:2000]
    prompt = f"""Question: {state['question']}

Generated SQL:
{state['sql']}

Columns: {state.get('columns')}
Result: {len(rows)} row(s). Sample: {sample}

This SQL ALREADY EXECUTED SUCCESSFULLY and returned the result above — so it is
syntactically valid. Do NOT judge SQL legality or style. In particular do NOT flag:
selecting columns that are functionally dependent on a GROUP BY primary key
(valid in PostgreSQL), CTEs, aliases, or formatting.

Judge ONLY whether it answers the question in MEANING:
- Right entities: the tables/columns match what the question asks about.
- Right relationships: joins follow real foreign keys (not two unrelated tables on
  id = id).
- Right filters: the column and value match the question's intent and time range.
  In particular, BETWEEN on a timestamp with an upper bound like '2022-07-31'
  drops the whole last day — the range must be half-open (>= start AND < next day).
- Right aggregation / grouping / ordering for what was asked. A COUNT(*) after a
  1-N join counts child rows, not the entities the question asks about.
- The result is plausible for the question (not obviously the wrong thing).

Default to valid. Mark it INVALID only if there is a concrete SEMANTIC error that
would give the user a wrong answer — and say exactly what.
Return JSON exactly: {{"valid": true/false, "reason": "...", "fix_hint": "..."}}"""
    try:
        resp = get_openai_client().chat.completions.create(
            model=REFLECT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a strict SQL reviewer. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        valid = bool(data.get("valid"))
        reason = str(data.get("reason", "")).strip()
        fix = str(data.get("fix_hint", "")).strip()
        logger.info("SQL reflect: valid=%s reason=%s", valid, reason)
        return {
            **state,
            "valid": valid,
            "verdict_reason": reason,
            "feedback": "" if valid else f"Your previous SQL was judged incorrect: {reason}. {fix}".strip(),
        }
    except Exception as e:
        # Never let a reviewer failure block a result — accept it, but don't loop.
        logger.warning("SQL reflect step failed (%s) — accepting result", e)
        return {**state, "valid": True, "verdict_reason": "reviewer unavailable"}


def _finalize_uncertain(state: SqlReActState) -> SqlReActState:
    """Retry budget exhausted while still not validated — keep the best effort,
    flagged so the answer can caveat it."""
    logger.warning("SQL ReAct: exhausted %d attempts without validation", MAX_SQL_ATTEMPTS)
    return {**state, "uncertain": True}


# ── Routing ──────────────────────────────────────────────────────────────────

def _route_after_execute(state: SqlReActState) -> str:
    if state.get("sql_error") == "empty query":
        # The generator declined (question not answerable from the schema) —
        # retrying the exact same prompt would return "" again. Give up now.
        return "give_up"
    if state.get("sql_error"):
        return "retry" if state.get("attempts", 0) < MAX_SQL_ATTEMPTS else "give_up"
    return "reflect"


def _route_after_reflect(state: SqlReActState) -> str:
    if state.get("valid"):
        return "end"
    return "retry" if state.get("attempts", 0) < MAX_SQL_ATTEMPTS else "uncertain"


def _build_sql_react_graph():
    g = StateGraph(SqlReActState)
    g.add_node("planner", _plan_node)
    g.add_node("generate", _generate_node)
    g.add_node("execute", _execute_node)
    g.add_node("reflect", _reflect_node)
    g.add_node("finalize_uncertain", _finalize_uncertain)

    g.set_entry_point("planner")
    g.add_edge("planner", "generate")
    g.add_edge("generate", "execute")
    g.add_conditional_edges(
        "execute", _route_after_execute,
        {"reflect": "reflect", "retry": "generate", "give_up": END},
    )
    g.add_conditional_edges(
        "reflect", _route_after_reflect,
        {"end": END, "retry": "generate", "uncertain": "finalize_uncertain"},
    )
    g.add_edge("finalize_uncertain", END)
    return g.compile()


# Compiled once.
sql_react_agent = _build_sql_react_graph()


def run_sql_react(question: str, schema: str, database_url: str, model: str,
                  max_rows: int, schema_graph=None, prior_sql: str = "") -> dict:
    """Run the Plan→Act→Reflect SQL loop; returns the final working state."""
    initial: SqlReActState = {
        "question": question, "db_schema": schema, "database_url": database_url,
        "model": model, "max_rows": max_rows, "schema_graph": schema_graph,
        "prior_sql": prior_sql or "",
        "plan": "", "join_paths": "", "sql": "", "columns": [], "rows": [],
        "sql_error": None, "feedback": "", "attempts": 0, "valid": False,
        "verdict_reason": "", "uncertain": False,
    }
    return sql_react_agent.invoke(initial)
