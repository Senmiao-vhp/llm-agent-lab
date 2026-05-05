"""根据 plan_result 执行工具，并合并知识图谱相关状态。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage

from app3.errors.classify import classify_exception
from app3.errors.envelope import ErrorEnvelope
from app3.errors.state import envelope_to_agent_patch
from app3.errors.taxonomy import RecoverableSubtype
from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState, ErrorClass


def _tools_by_name(ctx: GraphContext) -> dict[str, Any]:
    return {t.name: t for t in ctx.tools}


def _merge_kg_fields(
    state: AgentState,
    tool_name: str,
    output: Any,
) -> tuple[dict[str, Any] | None, list[str], list[dict[str, Any]] | None]:
    """基于单次工具结果更新 kg_context / linked_entities / kg_evidence。"""
    prev_ctx = state.get("kg_context")
    kg_context: dict[str, Any] = dict(prev_ctx) if isinstance(prev_ctx, dict) else {}

    linked = list(state.get("linked_entities") or [])
    prev_ev = state.get("kg_evidence")
    evidence: list[dict[str, Any]] = list(prev_ev) if isinstance(prev_ev, list) else []

    if isinstance(output, dict):
        if tool_name == "neo4j_resolve_region":
            for x in output.get("linked_entities") or []:
                if x and x not in linked:
                    linked.append(str(x))
            regions = output.get("regions") or []
            kg_context["neo4j_resolve_region"] = {
                "count": output.get("count"),
                "regions_preview": regions[:8],
            }
        elif tool_name == "neo4j_operator_dependencies":
            kg_context["neo4j_operator_dependencies"] = {
                "operator": output.get("operator"),
                "found": output.get("found"),
                "dependencies": output.get("dependencies") or [],
                "datasets": output.get("datasets") or [],
            }
        elif tool_name == "kg_graphrag_retrieve":
            ev = output.get("kg_evidence") or []
            if isinstance(ev, list):
                evidence.extend([e for e in ev if isinstance(e, dict)])
            kg_context["kg_graphrag_retrieve"] = {
                "status": output.get("status"),
                "message": output.get("message"),
            }

    kg_evidence_out: list[dict[str, Any]] | None = evidence if evidence else (prev_ev if isinstance(prev_ev, list) else None)
    return kg_context if kg_context else None, linked, kg_evidence_out


def _tool_output_for_state(output: Any) -> Any:
    if isinstance(output, (dict, list, str, int, float, bool)) or output is None:
        return output
    try:
        return json.loads(json.dumps(output, default=str))
    except (TypeError, ValueError):
        return str(output)


def act_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    plan = state.get("plan_result") or {}
    raw_calls = plan.get("tool_calls") or []
    if not raw_calls:
        return {
            "phase": "act",
            "error_class": ErrorClass.NONE,
            "last_tool_error": None,
            "recoverable_subtype": None,
            "last_error_message": None,
            "fatal_error": None,
            "fatal_subtype": None,
        }

    tools_map = _tools_by_name(ctx)
    tool_messages: list[ToolMessage] = []
    last_name: str | None = None
    last_output: Any = None

    patch_kg: dict[str, Any] = {}
    working: AgentState = dict(state)

    for tc in raw_calls:
        name = tc.get("name") if isinstance(tc, dict) else None
        if not name:
            continue
        name = str(name)
        args = tc.get("args") if isinstance(tc, dict) else {}
        if not isinstance(args, dict):
            args = {}
        call_id = tc.get("id") if isinstance(tc, dict) else None
        tool = tools_map.get(name)
        if tool is None:
            env = ErrorEnvelope(
                kind="recoverable",
                subtype=RecoverableSubtype.TOOL.value,
                message=f"unknown tool: {name}",
                source="act_node",
            )
            out = envelope_to_agent_patch(env)
            out["phase"] = "act"
            out["last_tool_error"] = f"unknown tool: {name}"
            return out

        try:
            output = tool.invoke(args)
        except Exception as exc:  # noqa: BLE001
            env = classify_exception(exc, source=f"tool:{name}")
            out = envelope_to_agent_patch(env)
            out["phase"] = "act"
            out["last_tool_name"] = name
            out["last_tool_error"] = str(exc).strip() or repr(exc)
            return out

        last_name = name
        last_output = output
        merged = _merge_kg_fields(working, name, output)
        kg_c, linked, kg_e = merged
        if kg_c is not None:
            patch_kg["kg_context"] = kg_c
            working["kg_context"] = kg_c
        patch_kg["linked_entities"] = linked
        working["linked_entities"] = linked
        if kg_e is not None:
            patch_kg["kg_evidence"] = kg_e
            working["kg_evidence"] = kg_e

        content = _tool_output_for_state(output)
        try:
            tool_content = json.dumps(content, ensure_ascii=False) if not isinstance(content, str) else content
        except (TypeError, ValueError):
            tool_content = str(content)

        tool_messages.append(
            ToolMessage(
                content=tool_content[:8000],
                tool_call_id=str(call_id or name),
            )
        )

    out: NodePatch = {
        "phase": "act",
        "error_class": ErrorClass.NONE,
        "last_tool_name": last_name,
        "last_tool_output": last_output,
        "last_tool_error": None,
        "recoverable_subtype": None,
        "last_error_message": None,
        "fatal_error": None,
        "fatal_subtype": None,
        **patch_kg,
    }
    if tool_messages:
        out["messages"] = tool_messages
    return out
