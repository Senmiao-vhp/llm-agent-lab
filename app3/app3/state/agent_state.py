"""LangGraph 状态模式 — 字段语义的单一来源（参见模块文档字符串）。"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ErrorClass:
    """为路由分类失败（由节点设置；边读取）。"""

    NONE = "none"
    RECOVERABLE = "recoverable"
    FATAL = "fatal"


class AgentState(TypedDict, total=False):
    """
    状态契约（开发阈值）：

    - `user_input` + `messages[0]` 应通过 `app3.state.initial_state.build_initial_state`
      在同一用户轮次中同时设置（保持基于token的和图规约器对齐）。
    - `error_class` + `last_error_message` 在 act 后驱动 `graph/edges`。
    - 路由字符串常量位于 `app3.graph.constants`（避免重复 `NodeName`）。
    - `fatal_error` 设置时表示不可重试的配置/认证问题 —— 边应 END。
    - `retry_count` 在进入恢复时在 `handle_error` 中递增；与 `max_retries` 比较。
    """

    messages: Annotated[list[AnyMessage], add_messages]
    user_input: str
    parse_result: dict[str, Any]
    plan_result: dict[str, Any]
    explain_result: dict[str, Any]
    last_tool_name: str | None
    last_tool_error: str | None
    last_tool_output: Any
    phase: str
    retry_count: int
    max_retries: int
    error_class: Literal["none", "recoverable", "fatal"]
    last_error_message: str | None
    fatal_error: str | None
