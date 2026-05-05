from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ExecutionMetrics(BaseModel):
    """执行性能指标收集器：精确统计每个任务和整体耗时"""

    start_time: float = Field(description="工作流开始时间戳")
    end_time: Optional[float] = Field(None, description="工作流结束时间戳")
    task_durations: Dict[str, float] = Field(default_factory=dict, description="每个任务秒级耗时")
    task_durations_ms: Dict[str, int] = Field(default_factory=dict, description="每个任务毫秒级耗时")

    @property
    def total_duration(self) -> float:
        """未结束则用当前时间估算"""
        end = self.end_time if self.end_time is not None else time.time()
        return round(end - self.start_time, 3)


class ExecutionResult(BaseModel):
    """执行结果统一返回格式"""

    success: bool = Field(description="执行是否完全成功")
    message: str = Field(description="人类可读状态信息")
    data: Optional[Dict[str, Any]] = Field(None, description="执行输出：包含 final_output + context")
    metrics: Optional[ExecutionMetrics] = Field(None, description="性能指标明细")


def default_gis_cache_dir() -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "data", "gis_cache")


@dataclass
class ExecutorConfig:
    """执行器配置（由 app3 Settings 注入）。"""

    gee_project_id: str
    cache_dir: str = field(default_factory=default_gis_cache_dir)
    use_cache: bool = True
