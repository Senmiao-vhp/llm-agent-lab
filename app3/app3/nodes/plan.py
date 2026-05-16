"""规划节点：可选 LLM 绑定工具，或固定 DSL → ``gis_execute_pipeline``。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app3.agents.planner_map import build_map_view
from app3.agents.planner_agent import build_plan_result_from_parse_dict
from app3.errors.classify import classify_exception
from app3.errors.planner import PlannerError
from app3.errors.state import envelope_to_agent_patch
from app3.errors.taxonomy import FatalSubtype
from app3.graph.context import GraphContext
from app3.kg.prompts import PLAN_KG_FIRST_SUPPLEMENT
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState, ErrorClass


def _format_parse_block(parse_result: dict[str, Any] | None) -> str:
    """
    格式化解析结果，输出结构化解析的关键信息文本块。
    :param parse_result: 结构化解析结果字典，通常包含 queries 列表等信息
    :return: 格式化后的字符串，描述解析的各子任务
    """
    pr = parse_result or {}
    queries = pr.get("queries") or []
    if not queries:
        return ""
    lines: list[str] = []
    for i, q in enumerate(queries[:5], 1):
        lines.append(
            f"子任务{i}: intent={q.get('intent')} | 区域={q.get('regions')} | "
            f"年份={q.get('time_range')} | 对象={q.get('target_object')} | "
            f"指标={q.get('specific_metrics')}"
        )
    src = pr.get("_parser_source")
    if src:
        lines.append(f"解析来源: {src}")
    return "【结构化解析】\n" + "\n".join(lines) + "\n"


def _serialize_tool_calls(ai: AIMessage) -> list[dict[str, Any]]:
    """
    将 AIMessage 中的 tool_calls 字段序列化为统一的 dict 列表。
    :param ai: 包含 tool_calls 属性的 AIMessage 实例
    :return: 工具调用的 dict 列表，每个 dict 包含 name, args, id 字段
    """
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


def _tool_names(ctx: GraphContext) -> set[str]:
    return {t.name for t in ctx.tools}


def plan_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    """
    ``plan_use_llm`` 且存在 ``ctx.llm`` 时走 LLM + ``bind_tools``；
    否则将 ``parse_result`` 编译为固定 DSL（``gis_execute_pipeline``）。
    """
    user_text = (state.get("user_input") or "").strip()
    parse_result = state.get("parse_result")
    pr = parse_result if isinstance(parse_result, dict) else {}
    queries = pr.get("queries") or []

    use_llm = bool(ctx.settings.plan_use_llm) and ctx.llm is not None

    if not use_llm:
        if not queries:
            return {
                "phase": "plan",
                "fatal_error": "DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。",
                "fatal_subtype": FatalSubtype.CONFIG.value,
                "error_class": ErrorClass.FATAL,
            }
        try:
            plan_result = build_plan_result_from_parse_dict(
                pr,
                user_text=user_text,
                tool_names=_tool_names(ctx),
            )
        except PlannerError as exc:
            env = classify_exception(exc, source="plan_node")
            patch = envelope_to_agent_patch(env)
            patch["phase"] = "plan"
            return patch
        return {
            "phase": "plan",
            "plan_result": plan_result,
            "error_class": ErrorClass.NONE,
            "fatal_error": None,
            "fatal_subtype": None,
            "recoverable_subtype": None,
            "last_error_message": None,
            "last_tool_error": None,
        }

    if ctx.llm is None:
        return {
            "phase": "plan",
            "fatal_error": "OPENAI_API_KEY is not set (or LLM factory failed).",
            "fatal_subtype": FatalSubtype.CONFIG.value,
            "error_class": ErrorClass.FATAL,
        }

    parse_block = _format_parse_block(parse_result if isinstance(parse_result, dict) else None)
    system_text = (
        "你是 GIS 智能体的规划模型：根据用户输入与下列结构化解析结果，选择并参数化应调用的工具（知识图谱与 GIS）。\n\n"
        + parse_block
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
    mv = build_map_view(pr, user_text)
    plan_result: dict[str, Any] = {
        "tool_calls": tool_calls,
        "content": ai.content,
        "source": "llm",
        "map_view": mv,
        "skip_gis": bool(mv.get("skip_gis")),
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
