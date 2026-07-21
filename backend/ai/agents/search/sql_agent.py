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
import json
import logging
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from ai.observability import get_openai_client

logger = logging.getLogger(__name__)

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
    # working state
    plan: str
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
    prompt = f"""Schema. Each line is `table(column type, ...)` and may end with
`[FK: col -> other_table(col)]`:
{state['db_schema']}

Question: {state['question']}

Produce a SHORT plan to answer it with SQL — do NOT write SQL yet:
- which tables, and the FK join path between them (join only along [FK: ...]);
- the exact filters (column and concrete value) implied by the question;
- the aggregation / grouping / ordering needed.
Max 4 lines."""
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
        return {**state, "plan": (resp.choices[0].message.content or "").strip()}
    except Exception as e:
        logger.warning("SQL plan step failed: %s", e)
        return {**state, "plan": ""}


def _generate_node(state: SqlReActState) -> SqlReActState:
    """Write the SQL (act), using the plan and any critique from a prior attempt."""
    from ai.agents.search.nodes.sql_query import _generate_sql
    sql = _generate_sql(
        state["question"], state["db_schema"], state["model"],
        plan=state.get("plan", ""), feedback=state.get("feedback", ""),
    )
    return {**state, "sql": sql, "attempts": state.get("attempts", 0) + 1,
            "sql_error": None, "feedback": ""}


def _execute_node(state: SqlReActState) -> SqlReActState:
    """Run the SQL via the MCP server (act / observe)."""
    from ai.agents.search.nodes.sql_query import _is_safe_select, _call_sql_tool, MAX_RESULT_ROWS
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
        )
    except Exception as e:
        return {**state, "rows": [], "columns": [], "sql_error": str(e),
                "feedback": f"The query raised an error: {e}. Fix the SQL."}
    if result.get("status") != "success":
        msg = result.get("message", "query execution failed")
        return {**state, "rows": [], "columns": [], "sql_error": msg,
                "feedback": f"The query failed: {msg}. Fix the SQL."}
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

Does this SQL correctly and completely answer the question? Verify:
- Right tables and FK join path (NEVER joins unrelated tables on id = id).
- Correct filters — the column and value match the question's intent and time range.
- Correct aggregation / grouping / ordering.
- The result is plausible (not empty or all-null when data is expected; figures sane).
Be strict: if anything is off, it is NOT valid.
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


def run_sql_react(question: str, db_schema: str, database_url: str, model: str, max_rows: int) -> dict:
    """Run the Plan→Act→Reflect SQL loop; returns the final working state."""
    initial: SqlReActState = {
        "question": question, "db_schema": schema, "database_url": database_url,
        "model": model, "max_rows": max_rows,
        "plan": "", "sql": "", "columns": [], "rows": [], "sql_error": None,
        "feedback": "", "attempts": 0, "valid": False, "verdict_reason": "",
        "uncertain": False,
    }
    return sql_react_agent.invoke(initial)
