"""结构化意图解析 — 仅 LLM；无模型或解析失败则 fatal（无占位）。"""

from __future__ import annotations

from typing import Any

from app3.agents.parser_agent import parse_composite_query
from app3.errors.classify import classify_exception
from app3.errors.state import envelope_to_agent_patch
from app3.errors.taxonomy import FatalSubtype
from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState, ErrorClass


def parse_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    user_text = (state.get("user_input") or "").strip()

    if ctx.llm is None:
        return {
            "phase": "parse",
            "fatal_error": "OPENAI_API_KEY is not set (or LLM factory failed); structured parse requires a chat model.",
            "fatal_subtype": FatalSubtype.CONFIG.value,
            "error_class": ErrorClass.FATAL,
        }

    try:
        cq = parse_composite_query(user_text, ctx.llm)
    except Exception as exc:  # noqa: BLE001 — 统一分类
        env = classify_exception(exc, source="parse_node")
        patch = envelope_to_agent_patch(env)
        patch["phase"] = "parse"
        return patch

    data: dict[str, Any] = cq.model_dump()
    data["_parser_source"] = "llm"

    return {
        "phase": "parse",
        "parse_result": data,
        "error_class": ErrorClass.NONE,
        "fatal_error": None,
        "fatal_subtype": None,
        "recoverable_subtype": None,
        "last_error_message": None,
        "last_tool_error": None,
    }
