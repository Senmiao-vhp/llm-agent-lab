"""GIS 包 — 重模块（WorkflowExecutor、GisOperators）需 `pip install -e .[gis]`。"""

from __future__ import annotations

from typing import Any

from app3.gis.types_dsl import OperatorType, TaskSpec, WorkflowPlan

__all__ = [
    "OperatorType",
    "TaskSpec",
    "WorkflowPlan",
    "ExecutionMetrics",
    "ExecutionResult",
    "ExecutorConfig",
    "WorkflowExecutor",
]


def __getattr__(name: str) -> Any:
    if name == "ExecutionMetrics":
        from app3.gis.executor_models import ExecutionMetrics

        return ExecutionMetrics
    if name == "ExecutionResult":
        from app3.gis.executor_models import ExecutionResult

        return ExecutionResult
    if name == "ExecutorConfig":
        from app3.gis.executor_models import ExecutorConfig

        return ExecutorConfig
    if name == "WorkflowExecutor":
        from app3.gis.executor_runtime import WorkflowExecutor

        return WorkflowExecutor
    raise AttributeError(name)
