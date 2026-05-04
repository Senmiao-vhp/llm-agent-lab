"""将失败标准化为状态 + 用户可见消息（存根实现）。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app3.nodes.base import NodePatch, bump_retry
from app3.state.agent_state import AgentState


def handle_error_node(state: AgentState) -> NodePatch:
    err = state.get("last_error_message") or state.get("fatal_error") or state.get("last_tool_error") or "unknown_error"
    r = bump_retry(state)
    return {
        "retry_count": r,
        "phase": "handle_error",
        "messages": [AIMessage(content=f"[recover_or_abort] {err}")],
    }
