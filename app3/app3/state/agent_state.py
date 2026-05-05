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
    状态契约：

    - `user_input` + `messages[0]` 由 `build_initial_state` 同步。
    - recoverable 路径：`recoverable_subtype`、`recovery_attempts`、按子类型的重试上限（见 `errors/policy`）。
    - fatal 路径：`fatal_subtype`、`fatal_error`；不含 API Key、用尽恢复次数等。
    - 知识图谱：`kg_context`（工具/查询摘要）、`linked_entities`（规范化 id）、`kg_evidence`（形态 C 证据链）。
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
    fatal_subtype: str | None
    recoverable_subtype: str | None
    recovery_attempts: dict[str, int]
    pending_sleep_seconds: float
    last_error_envelope: dict[str, Any] | None
    kg_context: dict[str, Any] | None
    linked_entities: list[str]
    kg_evidence: list[dict[str, Any]] | None
