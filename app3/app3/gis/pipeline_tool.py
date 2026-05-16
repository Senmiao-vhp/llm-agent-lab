"""LangChain 封装：`gis_execute_pipeline` — JSON DSL → WorkflowExecutor。"""

from __future__ import annotations

import json
from typing import Any

from app3.config import Settings
from app3.gis.executor_models import ExecutorConfig


def execute_pipeline_json(dsl_json: str, settings: Settings) -> dict[str, Any]:
    """
    执行 app3 GIS DSL（tasks + metadata），返回可 JSON 序列化的结果字典。
    """
    pid = (settings.gee_project_id or "").strip()
    if not pid:
        return {
            "success": False,
            "message": "GIS_PIPELINE_REQUIRES_GEE_PROJECT_ID",
            "error": "Configure GEE_PROJECT_ID in environment.",
        }

    try:
        dsl = json.loads(dsl_json)
    except json.JSONDecodeError as e:
        return {"success": False, "message": "INVALID_DSL_JSON", "error": str(e)}

    if not isinstance(dsl, dict):
        return {"success": False, "message": "DSL_MUST_BE_OBJECT", "error": str(type(dsl))}

    # 惰性导入：避免未安装 `[gis]` 时加载 rasterio/GEE 链
    from app3.gis.executor_runtime import WorkflowExecutor

    cfg = ExecutorConfig.from_settings(settings)
    ex = WorkflowExecutor(cfg)
    result = ex.execute(dsl)
    return result.model_dump()
