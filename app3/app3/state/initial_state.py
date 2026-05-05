"""初始状态构建器 — 保持 `user_input` 和 `messages` 的一致性。"""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from app3.state.agent_state import AgentState


def build_initial_state(
    user_input: str,
    *,
    max_retries: int = 3,
) -> AgentState:
    """
    `max_retries` 保留为向后兼容的全局默认：未知 recoverable 子类型时
    `errors.policy.get_max_retries` 可作 fallback。
    """
    text = (user_input or "").strip()
    return {
        "user_input": text,
        "messages": [HumanMessage(content=text)],
        "retry_count": 0,
        "max_retries": max_retries,
        "error_class": "none",
        "last_error_message": None,
        "fatal_error": None,
        "fatal_subtype": None,
        "recoverable_subtype": None,
        "recovery_attempts": {},
        "pending_sleep_seconds": 0.0,
        "last_error_envelope": None,
        "kg_context": None,
        "linked_entities": [],
        "kg_evidence": None,
        "gis_context": None,
    }
