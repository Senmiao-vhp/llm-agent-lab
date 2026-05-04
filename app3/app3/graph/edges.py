"""条件路由 — 纯函数，单元测试友好。"""

from __future__ import annotations

from typing import Literal

from app3.graph.constants import NodeName, RouteKey
from app3.state.agent_state import AgentState, ErrorClass


def route_after_parse(state: AgentState) -> Literal["plan", "end"]:
    if state.get("fatal_error"):
        return RouteKey.END
    return RouteKey.PLAN


def route_after_plan(state: AgentState) -> Literal["act", "end"]:
    if state.get("fatal_error"):
        return RouteKey.END
    return RouteKey.ACT


def route_after_act(state: AgentState) -> Literal["explain", "handle_error", "end"]:
    if state.get("fatal_error"):
        return RouteKey.END
    ec = state.get("error_class") or ErrorClass.NONE
    if ec == ErrorClass.RECOVERABLE:
        return NodeName.HANDLE_ERROR
    return RouteKey.EXPLAIN


def route_after_handle_error(state: AgentState) -> Literal["delay", "plan", "end"]:
    if state.get("fatal_error"):
        return RouteKey.END
    sleep_s = float(state.get("pending_sleep_seconds") or 0.0)
    if sleep_s > 0:
        return RouteKey.DELAY
    return RouteKey.PLAN


# 兼容旧名称（测试或外部引用）
route_after_error = route_after_handle_error
