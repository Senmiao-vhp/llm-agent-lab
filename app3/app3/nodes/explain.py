"""解读节点 — 先用确定性模板汇总 parse_result / plan_result / kg_evidence；
可选 APP3_EXPLAINER_LLM 再调用 LLM 生成面向用户的段落（对齐 app2 Explainer：模板优先，失败保留模板）。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState


def _template_summary(state: AgentState) -> str:
    """从 parse / plan / kg / gis 状态拼出确定性中文摘要；地图角色行仅在非 skip_gis 且角色非 none 时输出。"""
    pr = state.get("parse_result") or {}
    plan = state.get("plan_result") or {}
    kg_ev = state.get("kg_evidence") or []
    lines: list[str] = []

    for q in pr.get("queries") or []:
        lines.append(
            f"意图「{q.get('intent')}」：区域 {q.get('regions') or '—'}，"
            f"时间 {q.get('time_range') or '—'}，对象「{q.get('target_object')}」。"
        )
    tool_calls = plan.get("tool_calls") or []
    if tool_calls:
        names = [t.get("name") for t in tool_calls if isinstance(t, dict)]
        lines.append(f"规划调用工具：{', '.join(str(n) for n in names if n)}。")
    map_roles: list[str] = []
    wf = plan.get("workflow")
    if isinstance(wf, dict):
        meta = wf.get("metadata") or {}
        if isinstance(meta.get("map_inject_roles"), list):
            map_roles = [str(x) for x in meta["map_inject_roles"] if str(x) and str(x) != "none"]
    if not map_roles:
        mv = plan.get("map_view") or {}
        if isinstance(mv, dict) and isinstance(mv.get("map_inject_roles"), list):
            map_roles = [str(x) for x in mv["map_inject_roles"] if str(x) and str(x) != "none"]
    skip_gis = bool(plan.get("skip_gis"))
    if map_roles and not skip_gis:
        lines.append(f"建议地图图层角色：{', '.join(map_roles)}。")
    if plan.get("content"):
        c = str(plan.get("content")).strip()
        if c:
            lines.append(f"规划说明摘要：{c[:500]}{'…' if len(c) > 500 else ''}")
    if kg_ev:
        lines.append(f"知识图谱证据条目数：{len(kg_ev)}。")
    gis = state.get("gis_context")
    if isinstance(gis, dict) and gis:
        if "pipeline" in gis:
            p = gis["pipeline"]
            if isinstance(p, dict):
                lines.append(
                    f"GIS 流水线：success={p.get('success')}，{str(p.get('message') or '')[:400]}"
                )
        if "resolve_geometry" in gis:
            rg = gis["resolve_geometry"]
            if isinstance(rg, dict):
                lines.append(f"GIS 几何：区域 {rg.get('region')}，bbox={rg.get('bbox')}。")
    src = pr.get("_parser_source")
    if src:
        lines.append(f"（解析来源：{src}）")
    return "\n".join(lines) if lines else "本轮暂无结构化解析摘要；请查看工具输出与消息历史。"


def explain_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    """生成 explain_result（模板摘要，可选 LLM 段落）并追加一条 AIMessage 便于用户阅读。"""
    summary = _template_summary(state)
    explain_result: dict[str, Any] = {
        "summary": summary,
        "source": "template",
    }

    use_llm = ctx.settings.explainer_llm
    if use_llm and ctx.llm is not None:
        try:
            sys = SystemMessage(
                content="你是农业 GIS 助手：根据给定状态用简洁中文总结执行要点，不要编造未出现的数值。"
            )
            human = HumanMessage(
                content=f"解析与规划摘要请求：\n{summary}\n\n若 messages 中有工具结果请一并概括。"
            )
            ai = ctx.llm.invoke([sys, human])
            text = ai.content if hasattr(ai, "content") else str(ai)
            if isinstance(text, str) and text.strip():
                explain_result["llm_paragraph"] = text.strip()
                explain_result["source"] = "template+llm"
                summary = text.strip()
        except Exception:
            explain_result["llm_error"] = "解释模型调用失败，已保留模板摘要。"

    return {
        "phase": "explain",
        "explain_result": explain_result,
        "messages": [AIMessage(content=summary)],
    }
