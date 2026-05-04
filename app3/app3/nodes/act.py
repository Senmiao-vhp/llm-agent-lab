"""工具执行 — 在学习 LangGraph 模式时替换为预构建的 ToolNode。"""

from __future__ import annotations

from typing import Any

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState, ErrorClass


def act_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    _ = ctx, state
    # TODO: 根据 plan_result 分发 ctx.tools；成功时：
    #       返回 { error_class: ErrorClass.NONE, last_tool_error: None, ... }
    #       可恢复的工具失败时：
    #       返回 { error_class: ErrorClass.RECOVERABLE, last_error_message: "...", last_tool_error: "..." }
    return {"phase": "act", "error_class": ErrorClass.NONE}
