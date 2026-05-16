"""GIS 包 — 重模块（WorkflowExecutor、GisOperators）需 `pip install -e .[gis]`。

行政区离线归一 ``district_normalize`` 仅依赖标准库，可从本包直接导入。
"""

from __future__ import annotations

from typing import Any

from app3.gis.district_normalize import (
    DistrictNormalizer,
    is_district_canonical,
    normalize_region,
    normalize_regions,
    regions_are_all_district_canonical,
)
from app3.gis.types_dsl import OperatorType, TaskSpec, WorkflowPlan

__all__ = [
    "DistrictNormalizer",
    "OperatorType",
    "TaskSpec",
    "WorkflowPlan",
    "ExecutionMetrics",
    "ExecutionResult",
    "ExecutorConfig",
    "WorkflowExecutor",
    "is_district_canonical",
    "normalize_region",
    "normalize_regions",
    "regions_are_all_district_canonical",
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
