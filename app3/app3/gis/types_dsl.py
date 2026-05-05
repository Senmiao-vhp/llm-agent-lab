"""GIS 工作流 DSL — 与 app2 `planner_types` 对齐。"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OperatorType(str, Enum):
    RESOLVE_GEOMETRY = "resolve_geometry"
    LOAD_GLOBELAND30 = "load_globeland30"
    SEARCH_SATELLITE = "search_satellite"
    CALCULATE_NDVI = "calculate_ndvi"
    DETECT_CHANGE = "detect_change"
    AREA_STATS = "area_stats"
    CALCULATE_HOLDINGS = "calculate_holdings"
    TREND_CROPLAND_LOSS = "trend_cropland_loss"
    COMPLIANCE_CHECK_POINT = "compliance_check_point"
    REGION_COMPARE_BASELINE = "region_compare_baseline"
    LAND_TRANSFER_AFTER_LOSS = "land_transfer_after_loss"


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
        description="任务唯一 ID；多意图时可加 q1_/q2_ 前缀",
    )
    op: OperatorType
    params: Dict[str, Any] = Field(default_factory=dict)
    inputs: List[str] = Field(default_factory=list)

    @field_validator("inputs")
    @classmethod
    def _validate_inputs(cls, v: List[str]) -> List[str]:
        for item in v:
            if item.startswith("$"):
                continue
            raise ValueError("inputs only supports $taskId.output references in GIS DSL.")
        return v


class WorkflowPlan(BaseModel):
    tasks: List[TaskSpec]
    metadata: Dict[str, Any] = Field(default_factory=dict)
