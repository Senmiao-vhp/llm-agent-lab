"""将失败标准化为状态 + 用户可见消息；按子类型计数、指数退避或终止。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app3.errors.policy import compute_backoff_seconds, get_max_retries
from app3.errors.taxonomy import FatalSubtype, RecoverableSubtype
from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch, bump_retry
from app3.state.agent_state import AgentState, ErrorClass


def handle_error_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    subtype = (state.get("recoverable_subtype") or RecoverableSubtype.UNKNOWN.value).strip()
    attempts = dict(state.get("recovery_attempts") or {})
    attempts[subtype] = attempts.get(subtype, 0) + 1

    fallback_max = int(state.get("max_retries") or 3)
    max_r = get_max_retries(subtype, fallback=fallback_max)

    err_msg = state.get("last_error_message") or state.get("last_tool_error") or "unknown_error"

    if attempts[subtype] > max_r:
        fatal_msg = f"恢复次数已用尽 ({subtype}, 上限 {max_r}): {err_msg}"
        return {
            "recovery_attempts": attempts,
            "retry_count": bump_retry(state),
            "fatal_error": fatal_msg,
            "fatal_subtype": FatalSubtype.RETRIES_EXHAUSTED.value,
            "error_class": ErrorClass.FATAL,
            "recoverable_subtype": None,
            "pending_sleep_seconds": 0.0,
            "phase": "handle_error",
            "messages": [AIMessage(content=f"[aborted] {fatal_msg}")],
        }

    attempt_index = attempts[subtype] - 1
    sleep_s = compute_backoff_seconds(subtype, attempt_index, settings=ctx.settings)
    return {
        "recovery_attempts": attempts,
        "retry_count": bump_retry(state),
        "pending_sleep_seconds": sleep_s,
        "phase": "handle_error",
        "messages": [AIMessage(content=f"[recover_{subtype}] {err_msg}")],
    }
