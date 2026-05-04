"""通过 LLM 进行规划 — 实现待完成。"""

from __future__ import annotations

from typing import Any

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState


def plan_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    _ = ctx, state
    # TODO: 使用 parse_result；生成 plan_result（工具名称/参数）
    return {"phase": "plan"}
