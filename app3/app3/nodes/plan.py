"""通过 LLM 进行规划 — 绑定技能工具并产出 tool_calls。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app3.errors.classify import classify_exception
from app3.errors.state import envelope_to_agent_patch
from app3.errors.taxonomy import FatalSubtype
from app3.graph.context import GraphContext
from app3.kg.prompts import PLAN_KG_FIRST_SUPPLEMENT
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState, ErrorClass


def _serialize_tool_calls(ai: AIMessage) -> list[dict[str, Any]]:
    raw = getattr(ai, "tool_calls", None) or []
    out: list[dict[str, Any]] = []
    for tc in raw:
        if isinstance(tc, dict):
            name = tc.get("name")
            args = tc.get("args") if tc.get("args") is not None else {}
            tid = tc.get("id")
        else:
            name = getattr(tc, "name", None)
            args = getattr(tc, "args", None) or {}
            tid = getattr(tc, "id", None)
        if name:
            out.append({"name": str(name), "args": dict(args) if isinstance(args, dict) else {}, "id": tid})
    return out


def plan_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    """
    使用 `ctx.llm.bind_tools` 生成规划消息；将 `PLAN_KG_FIRST_SUPPLEMENT` 并入 system，
    强调先查 Neo4j 再编排 GIS。
    """
    if ctx.llm is None:
        return {
            "phase": "plan",
            "fatal_error": "OPENAI_API_KEY is not set (or LLM factory failed).",
            "fatal_subtype": FatalSubtype.CONFIG.value,
            "error_class": ErrorClass.FATAL,
        }

    user_text = (state.get("user_input") or "").strip()
    system_text = (
        "你是 GIS 智能体的规划模型：根据用户输入，选择并参数化应调用的工具（知识图谱与 GIS）。\n\n"
        + PLAN_KG_FIRST_SUPPLEMENT.strip()
    )
    messages = [
        SystemMessage(content=system_text),
        HumanMessage(content=user_text or "(empty)"),
    ]

    bound = ctx.llm.bind_tools(list(ctx.tools))
    try:
        ai = bound.invoke(messages)
    except Exception as exc:  # noqa: BLE001 — 统一分类
        env = classify_exception(exc, source="plan_node")
        patch = envelope_to_agent_patch(env)
        patch["phase"] = "plan"
        return patch

    if not isinstance(ai, AIMessage):
        ai = AIMessage(content=str(ai))

    tool_calls = _serialize_tool_calls(ai)
    plan_result: dict[str, Any] = {
        "tool_calls": tool_calls,
        "content": ai.content,
    }

    return {
        "phase": "plan",
        "messages": [ai],
        "plan_result": plan_result,
        "error_class": ErrorClass.NONE,
        "fatal_error": None,
        "fatal_subtype": None,
        "recoverable_subtype": None,
        "last_error_message": None,
        "last_tool_error": None,
    }
