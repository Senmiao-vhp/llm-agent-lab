"""共享的节点返回类型定义。"""

from __future__ import annotations

from typing import Any, TypedDict


class NodePatch(TypedDict, total=False):
    """节点状态补丁类型，用于在 LangGraph 节点之间传递状态更新。

    所有字段均为可选，允许节点只更新需要修改的状态部分。
    """
    phase: str  # 当前执行阶段标识
    retry_count: int  # 当前重试次数计数
    fatal_error: str | None  # 致命错误信息，如有则终止流程
    parse_result: dict[str, Any]  # 解析阶段的结果数据
    plan_result: dict[str, Any]  # 规划阶段的结果数据
    explain_result: dict[str, Any]  # 解释阶段的结果数据
    last_tool_name: str | None  # 最后调用的工具名称
    last_tool_error: str | None  # 最后工具调用的错误信息
    last_tool_output: Any  # 最后工具调用的输出结果
    error_class: str  # 错误类型分类标识
    last_error_message: str | None  # 最后的错误描述信息

def bump_retry(state: dict[str, Any]) -> int:
    return int(state.get("retry_count") or 0) + 1
