"""仅通过 LLM 解析用户意图 — 实现待完成。"""

from __future__ import annotations

from typing import Any

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState


def parse_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    _ = state
    if ctx.llm is None:
        return {
            "phase": "parse",
            "fatal_error": "OPENAI_API_KEY is not set (or LLM factory failed).",
        }
    # TODO: 实现 ctx.llm.with_structured_output(...) -> parse_result
    # TODO: 在 LLMInvocationError 时根据策略设置可恢复/致命错误字段
    return {"phase": "parse"}
