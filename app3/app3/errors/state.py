"""将 ErrorEnvelope 转为写入 AgentState 的补丁字段。"""

from __future__ import annotations

from typing import Any

from app3.errors.envelope import ErrorEnvelope
from app3.state.agent_state import ErrorClass


def envelope_to_agent_patch(env: ErrorEnvelope) -> dict[str, Any]:
    """合并进节点返回值时使用。"""
    patch: dict[str, Any] = {
        "last_error_envelope": env.to_dict(),
        "last_error_message": env.message,
    }
    if env.kind == "fatal":
        patch["error_class"] = ErrorClass.FATAL
        patch["fatal_subtype"] = env.subtype
        patch["recoverable_subtype"] = None
        patch["fatal_error"] = env.message
    else:
        patch["error_class"] = ErrorClass.RECOVERABLE
        patch["recoverable_subtype"] = env.subtype
        patch["fatal_error"] = None
        patch["fatal_subtype"] = None
    return patch
