"""仅通过 LLM 进行解释 — 实现待完成。"""

from __future__ import annotations

from typing import Any

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState


def explain_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    _ = ctx, state
    # TODO: ctx.llm -> explain_result + 通过 messages 附加助手消息
    return {"phase": "explain"}
