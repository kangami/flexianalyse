"""LangGraph pipeline for model answer generation.

Inline citations ([document, p.X]) are enforced by the system prompt instructions,
not by post-processing. This keeps citations in context, sentence by sentence.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Tuple

from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

ModelExecutor = Callable[[str, str, str], Awaitable[Tuple[str, str]]]


class AnswerGraphState(TypedDict, total=False):
    prompt: str
    selected_model: str
    user_query: str
    answer: str
    model_used: str


async def run_answer_graph(
    *,
    prompt: str,
    selected_model: str,
    user_query: str,
    directory_content: List[Dict[str, Any]],
    model_executor: ModelExecutor,
) -> Tuple[str, str]:
    """
    Run the answer-generation pipeline via LangGraph.

    The graph has a single node: generate_answer.
    Inline citations are produced by the model itself (enforced in the system prompt).
    Falls back to a direct model call if LangGraph fails.
    """
    try:
        from langgraph.graph import END, StateGraph

        async def generate_answer(state: AnswerGraphState) -> AnswerGraphState:
            response, model_used = await model_executor(
                state["prompt"],
                state["selected_model"],
                state["user_query"],
            )
            return {"answer": response, "model_used": model_used}

        graph = StateGraph(AnswerGraphState)
        graph.add_node("generate_answer", generate_answer)
        graph.set_entry_point("generate_answer")
        graph.add_edge("generate_answer", END)

        app = graph.compile()
        out = await app.ainvoke(
            {
                "prompt": prompt,
                "selected_model": selected_model,
                "user_query": user_query,
            }
        )
        return out.get("answer", ""), out.get("model_used", selected_model)

    except Exception as exc:
        logger.warning("LangGraph pipeline failed (%s) – using direct model call", exc)
        return await model_executor(prompt, selected_model, user_query)
