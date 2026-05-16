from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app3.config import Settings


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
    processed_data_dir: str = ""
    globeland30_dir: str = ""
    raw_admin_boundary_dir: str = ""
    processed_admin_boundary_dir: str = ""
    geo_fallback_nominatim: bool = False
    executor_parallel: bool = True
    executor_parallel_workers: int | None = None

    @staticmethod
    def from_settings(settings: Settings) -> ExecutorConfig:
        cache_dir = (settings.gis_cache_dir or "").strip() or default_gis_cache_dir()
        return ExecutorConfig(
            gee_project_id=(settings.gee_project_id or "").strip(),
            cache_dir=cache_dir,
            use_cache=settings.gis_use_cache,
            processed_data_dir=settings.processed_data_dir,
            globeland30_dir=settings.globeland30_dir,
            raw_admin_boundary_dir=settings.raw_admin_boundary_dir,
            processed_admin_boundary_dir=settings.processed_admin_boundary_dir,
            geo_fallback_nominatim=settings.geo_fallback_nominatim,
            executor_parallel=settings.executor_parallel,
            executor_parallel_workers=settings.executor_parallel_workers,
        )
