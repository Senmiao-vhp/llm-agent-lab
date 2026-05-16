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
    """LangGraph 单轮（单 thread）图状态：各节点返回 patch 合并进此 dict。

    - **输入与消息**：`user_input` 与 `messages`；初始由 `build_initial_state` 对齐首条用户语与 `messages[0]`。
    - **阶段产物**：`parse_result` / `plan_result` / `explain_result`；`phase` 标记当前节点语义。
    - **工具调用**：`last_tool_name`、`last_tool_error`、`last_tool_output` 记录最近一次工具结果。
    - **重试**：`retry_count`、`max_retries`；可恢复失败时配合 `recovery_attempts`、`recoverable_subtype` 与 `pending_sleep_seconds`（退避由 `errors/policy` 等计算）。
    - **错误分类**：`error_class`（none / recoverable / fatal）；致命路径写 `fatal_error`、`fatal_subtype`；结构化详情可放在 `last_error_envelope`。
    - **知识图谱**：`kg_context`（工具侧摘要）、`linked_entities`（规范化实体 id）、`kg_evidence`（GraphRAG 等证据列表）。
    - **GIS**：`gis_context`（工具侧摘要；完整 pipeline 结果见 `gis_execute_pipeline`）。
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
    gis_context: dict[str, Any] | None
