"""GIS LangChain 工具：轻量 Nominatim + 可选完整算子栈与 pipeline。"""

from __future__ import annotations

from collections.abc import Sequence
from functools import partial
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app3.config import Settings
from app3.gis.availability import gis_stack_importable
from app3.skills.gis.bbox_area import approximate_bbox_area_sqm
from app3.skills.gis.nominatim import nominatim_resolve_region


class ResolveGeometryArgs(BaseModel):
    region: str = Field(description="可读的区域名称，例如「成都市郫都区」「北京市」。")


class EstimateBboxAreaArgs(BaseModel):
    west: float = Field(description="边界框西经（度），须小于 east。")
    south: float = Field(description="边界框南纬（度），须小于 north。")
    east: float = Field(description="边界框东经（度）。")
    north: float = Field(description="边界框北纬（度）。")


class GisPipelineArgs(BaseModel):
    dsl_json: str = Field(
        description=(
            'GIS 工作流 DSL JSON 字符串，顶层含 "tasks" 数组；每项含 id、op、params、inputs（依赖形如 "$taskId.output"）。'
            "op 为 resolve_geometry | load_globeland30 | search_satellite | calculate_ndvi | detect_change | "
            "area_stats | calculate_holdings | trend_cropland_loss | compliance_check_point | "
            "region_compare_baseline | land_transfer_after_loss。"
        ),
    )


def _resolve_geometry(region: str, *, settings: Settings) -> dict[str, Any]:
    """优先使用完整 GisOperators（需 `[gis]` + GEE 项目）；否则回退 Nominatim。"""
    if gis_stack_importable() and (settings.gee_project_id or "").strip():
        try:
            from app3.gis.gee_client import GeeClient, GeeConfig
            from app3.gis.operators import GisOperators

            ops = GisOperators(GeeClient(GeeConfig(project_id=(settings.gee_project_id or "").strip())))
            return ops.resolve_geometry({"region": region}, None)
        except Exception:
            pass
    return nominatim_resolve_region(region)


def _estimate_bbox_area(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    base = approximate_bbox_area_sqm(west, south, east, north)
    return {"type": "area_stats_estimate", **base}


def _gis_execute_pipeline(dsl_json: str, *, settings: Settings) -> dict[str, Any]:
    if not gis_stack_importable():
        return {
            "success": False,
            "message": "GIS_STACK_NOT_INSTALLED",
            "error": "Install optional extras: pip install -e .[gis]",
        }
    from app3.gis.pipeline_tool import execute_pipeline_json

    return execute_pipeline_json(dsl_json, settings)


def build_gis_tools(settings: Settings) -> Sequence[StructuredTool]:
    tools: list[StructuredTool] = [
        StructuredTool.from_function(
            name="resolve_geometry",
            description=(
                "将行政区/地名解析为边界 GeoJSON 与 bbox。"
                "若已配置 APP3_GEE_PROJECT_ID 且安装 `[gis]` extras，则走与 app2 相同的解析链（GEE/本地边界/Nominatim）；"
                "否则仅用 OSM Nominatim（见 APP3_GIS_NOMINATIM）。"
            ),
            args_schema=ResolveGeometryArgs,
            func=partial(_resolve_geometry, settings=settings),
        ),
        StructuredTool.from_function(
            name="estimate_bbox_area",
            description=(
                "根据经纬度 bbox（度）粗算地表面积（亩/公顷），球面近似；"
                "典型输入来自 resolve_geometry 返回的 bbox [west,south,east,north]。"
            ),
            args_schema=EstimateBboxAreaArgs,
            func=_estimate_bbox_area,
        ),
    ]
    if gis_stack_importable():
        tools.append(
            StructuredTool.from_function(
                name="gis_execute_pipeline",
                description=(
                    "执行完整 GIS 算子 DAG（与 app2 WorkflowExecutor 相同）。"
                    "参数 dsl_json 为 JSON 字符串：{\"tasks\":[{\"id\",\"op\",\"params\",\"inputs\"}], \"metadata\":{...}}。"
                    "需要有效的 Earth Engine 项目（APP3_GEE_PROJECT_ID）与本地 GlobeLand/行政区数据路径（APP3_DATA_DIR 等）。"
                ),
                args_schema=GisPipelineArgs,
                func=partial(_gis_execute_pipeline, settings=settings),
            )
        )
    return tools


def build_gis_placeholder_tools() -> Sequence[StructuredTool]:
    """兼容旧 API：需传入 Settings 时请改用 build_gis_tools(Settings.from_env())。"""
    from app3.config import Settings as S

    return build_gis_tools(S.from_env())
