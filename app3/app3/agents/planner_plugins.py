"""内置意图规划插件"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app3.agents.planner_registry import register_builtin_plan_handler
from app3.agents.planner_types import OperatorType, TaskSpec
from app3.contracts.intents import IntentId
from app3.contracts.query import QueryIntent
from app3.errors.planner import PlannerPlanningError


@dataclass
class PlanningContext:
    """单次规划调用上下文：planner 数值参数 + 是否导出/展示图斑相关 UI 开关。"""
    params: dict[str, Any]
    ui_show_polygons: bool = False


def _pick_region(intent: QueryIntent) -> str:
    """取首个行政区；无 regions 时抛出规划类错误（需用户补全区划）。"""
    if not intent.regions:
        raise PlannerPlanningError("intent.regions is required (at least one region).")
    return intent.regions[0]


def _pick_year(intent: QueryIntent, default_year: int = 2020) -> int:
    """从 time_range 取最大年份作为代表年；解析失败则用 default_year。"""
    if intent.time_range:
        try:
            return int(sorted(intent.time_range)[-1])
        except Exception:
            pass
    return default_year


def _years_for_trend(intent: QueryIntent) -> list[int]:
    """趋势分析用年份列表：优先用 time_range 内合法年；否则用近年窗口（受当前年上界约束）。"""
    now = datetime.now().year
    y_max = now - 1
    if intent.time_range:
        ys: list[int] = []
        for x in intent.time_range:
            try:
                y = int(x)
            except (TypeError, ValueError):
                continue
            if 2015 <= y <= y_max:
                ys.append(y)
        ys = sorted(set(ys))
        if len(ys) >= 2:
            return ys[:8]
        if len(ys) == 1:
            y0 = ys[0]
            w = [y0 - 2, y0 - 1, y0, y0 + 1, y0 + 2]
            return [y for y in w if 2015 <= y <= y_max]
    end = y_max
    if end < 2019:
        end = 2019
    return [end - 4, end - 3, end - 2, end - 1, end]


def plan_current_status(ctx: PlanningContext, intent: QueryIntent) -> list[TaskSpec]:
    """现状估计：Globeland 基线 + 统计；若对比年非 2020 则追加卫星/NDVI/变化与持仓任务链。"""
    region = _pick_region(intent)
    year = _pick_year(intent, default_year=2020)
    thr = float(ctx.params.get("ndvi_threshold", 0.15))
    max_cloud = float((ctx.params.get("search_satellite") or {}).get("max_cloud_cover", 20.0))
    cd = ctx.params.get("change_detection") or {}
    max_features = int(cd.get("max_features", 5000))
    tasks: list[TaskSpec] = [
        TaskSpec(id="geom", op=OperatorType.RESOLVE_GEOMETRY, params={"region": region}, inputs=[]),
        TaskSpec(
            id="baseline_mask",
            op=OperatorType.LOAD_GLOBELAND30,
            params={
                "region": region,
                "target_object": intent.target_object,
                "export_geojson": bool(ctx.ui_show_polygons),
                "max_features": max_features,
                "min_feature_area_pixels": 0,
            },
            inputs=["$geom.output"],
        ),
        TaskSpec(
            id="baseline_stats",
            op=OperatorType.AREA_STATS,
            params={"label": "2020_baseline"},
            inputs=["$baseline_mask.output"],
        ),
    ]
    if year != 2020:
        tasks.extend(
            [
                TaskSpec(
                    id="sat",
                    op=OperatorType.SEARCH_SATELLITE,
                    params={"region": region, "year": year, "max_cloud_cover": max_cloud},
                    inputs=["$geom.output"],
                ),
                TaskSpec(id="ndvi", op=OperatorType.CALCULATE_NDVI, params={}, inputs=["$sat.output"]),
                TaskSpec(
                    id="loss_mask",
                    op=OperatorType.DETECT_CHANGE,
                    params={
                        "ndvi_threshold": thr,
                        "export_geojson": bool(ctx.ui_show_polygons),
                        "max_features": max_features,
                    },
                    inputs=["$baseline_mask.output", "$ndvi.output", "$sat.output"],
                ),
                TaskSpec(
                    id="loss_stats",
                    op=OperatorType.AREA_STATS,
                    params={"label": f"loss_2020_{year}"},
                    inputs=["$loss_mask.output"],
                ),
                TaskSpec(
                    id="holdings",
                    op=OperatorType.CALCULATE_HOLDINGS,
                    params={"year": year, "cache_buster": "holdings_v2"},
                    inputs=["$baseline_stats.output", "$loss_stats.output"],
                ),
            ]
        )
    return tasks


def plan_change_detection(ctx: PlanningContext, intent: QueryIntent) -> list[TaskSpec]:
    """变化检测：几何 → 基线掩膜 → 当年影像 NDVI → 变化掩膜与面积统计。"""
    region = _pick_region(intent)
    year = _pick_year(intent, default_year=2023)
    thr = float(ctx.params.get("ndvi_threshold", 0.15))
    max_cloud = float((ctx.params.get("search_satellite") or {}).get("max_cloud_cover", 20.0))
    cd = ctx.params.get("change_detection") or {}
    export_geojson = bool(cd.get("export_geojson", True)) or ctx.ui_show_polygons
    max_features = int(cd.get("max_features", 5000))
    return [
        TaskSpec(id="geom", op=OperatorType.RESOLVE_GEOMETRY, params={"region": region}, inputs=[]),
        TaskSpec(
            id="baseline_mask",
            op=OperatorType.LOAD_GLOBELAND30,
            params={
                "region": region,
                "target_object": intent.target_object,
                "export_geojson": export_geojson,
                "max_features": max_features,
                "min_feature_area_pixels": 0,
            },
            inputs=["$geom.output"],
        ),
        TaskSpec(
            id="sat",
            op=OperatorType.SEARCH_SATELLITE,
            params={"region": region, "year": year, "max_cloud_cover": max_cloud},
            inputs=["$geom.output"],
        ),
        TaskSpec(id="ndvi", op=OperatorType.CALCULATE_NDVI, params={}, inputs=["$sat.output"]),
        TaskSpec(
            id="change_mask",
            op=OperatorType.DETECT_CHANGE,
            params={"ndvi_threshold": thr, "export_geojson": export_geojson, "max_features": max_features},
            inputs=["$baseline_mask.output", "$ndvi.output", "$sat.output"],
        ),
        TaskSpec(
            id="change_stats",
            op=OperatorType.AREA_STATS,
            params={"label": f"change_{year}"},
            inputs=["$change_mask.output"],
        ),
    ]


def plan_trend_evolution(ctx: PlanningContext, intent: QueryIntent) -> list[TaskSpec]:
    """趋势演变：单条 TREND_CROPLAND_LOSS，年份与并行等参数来自 ctx.params。"""
    region = _pick_region(intent)
    years = _years_for_trend(intent)
    thr = float(ctx.params.get("ndvi_threshold", 0.15))
    tr = ctx.params.get("trend") or {}
    par = ctx.params.get("parallel") or {}
    return [
        TaskSpec(id="geom", op=OperatorType.RESOLVE_GEOMETRY, params={"region": region}, inputs=[]),
        TaskSpec(
            id="trend",
            op=OperatorType.TREND_CROPLAND_LOSS,
            params={
                "region": region,
                "target_object": intent.target_object,
                "ndvi_threshold": thr,
                "years": years,
                "max_cloud_cover": float(tr.get("max_cloud_cover", 40.0)),
                "scale_m": int(tr.get("scale_m", 200)),
                "download_timeout": int(tr.get("download_timeout", 360)),
                "date_half_width_days": int(tr.get("date_half_width_days", 40)),
                "per_year_retries": int(tr.get("per_year_retries", 3)),
                "retry_sleep_s": tr.get("retry_sleep_s", [4.0, 8.0]),
                "parallel_years": bool(tr.get("parallel_years", False)),
                "parallel_workers": int(tr.get("parallel_workers", int(par.get("max_workers", 4)))),
            },
            inputs=["$geom.output"],
        ),
    ]


def plan_compliance_check(ctx: PlanningContext, intent: QueryIntent) -> list[TaskSpec]:
    """合规/点位核查：有坐标则单任务点查；否则先 resolve_geometry 再用行政区中心。"""
    year = _pick_year(intent, default_year=2023)
    thr = float(ctx.params.get("ndvi_threshold", 0.15))
    if intent.coordinates and len(intent.coordinates) > 0:
        lon, lat = float(intent.coordinates[0][0]), float(intent.coordinates[0][1])
        return [
            TaskSpec(
                id="compliance",
                op=OperatorType.COMPLIANCE_CHECK_POINT,
                params={
                    "lon": lon,
                    "lat": lat,
                    "target_object": intent.target_object,
                    "year": year,
                    "ndvi_threshold": thr,
                    "location_mode": "coordinates",
                },
                inputs=[],
            )
        ]
    region = _pick_region(intent)
    return [
        TaskSpec(id="geom", op=OperatorType.RESOLVE_GEOMETRY, params={"region": region}, inputs=[]),
        TaskSpec(
            id="compliance",
            op=OperatorType.COMPLIANCE_CHECK_POINT,
            params={
                "use_bbox_center": True,
                "target_object": intent.target_object,
                "year": year,
                "ndvi_threshold": thr,
                "location_mode": "admin_bbox_center",
            },
            inputs=["$geom.output"],
        ),
    ]


def plan_multi_region_compare(ctx: PlanningContext, intent: QueryIntent) -> list[TaskSpec]:
    """多区域对比：至少两个 regions，否则抛 PlannerPlanningError；单任务 REGION_COMPARE_BASELINE。"""
    if not intent.regions or len(intent.regions) < 2:
        raise PlannerPlanningError(
            "多区域对比需要至少两个行政区，例如：「对比北京市和河北省的耕地面积」。"
        )
    par = ctx.params.get("parallel") or {}
    return [
        TaskSpec(
            id="compare",
            op=OperatorType.REGION_COMPARE_BASELINE,
            params={
                "regions": intent.regions[:6],
                "target_object": intent.target_object,
                "parallel_enabled": bool(par.get("enabled", True)),
                "parallel_workers": int(par.get("max_workers", 4)),
            },
            inputs=[],
        )
    ]


def plan_transfer_analysis(ctx: PlanningContext, intent: QueryIntent) -> list[TaskSpec]:
    """流转分析：几何解析后接 LAND_TRANSFER_AFTER_LOSS（区划 + 年 + NDVI 阈值）。"""
    region = _pick_region(intent)
    year = _pick_year(intent, default_year=2023)
    thr = float(ctx.params.get("ndvi_threshold", 0.15))
    return [
        TaskSpec(id="geom", op=OperatorType.RESOLVE_GEOMETRY, params={"region": region}, inputs=[]),
        TaskSpec(
            id="transfer",
            op=OperatorType.LAND_TRANSFER_AFTER_LOSS,
            params={
                "region": region,
                "year": year,
                "target_object": intent.target_object,
                "ndvi_threshold": thr,
            },
            inputs=["$geom.output"],
        ),
    ]


def plan_other(_ctx: PlanningContext, _intent: QueryIntent) -> list[TaskSpec]:
    """非 GIS 意图：不生成任务（由上层 metadata / skip_gis 处理）。"""
    return []


def register_builtin_plan_handlers() -> None:
    """将各 IntentId 与内置 plan 函数注册到 planner_registry（模块 import 时自动执行一次）。"""
    register_builtin_plan_handler(IntentId.CURRENT_STATUS_ESTIMATE.value, plan_current_status)
    register_builtin_plan_handler(IntentId.CHANGE_DETECTION.value, plan_change_detection)
    register_builtin_plan_handler(IntentId.TREND_EVOLUTION.value, plan_trend_evolution)
    register_builtin_plan_handler(IntentId.COMPLIANCE_CHECK.value, plan_compliance_check)
    register_builtin_plan_handler(IntentId.MULTI_REGION_COMPARE.value, plan_multi_region_compare)
    register_builtin_plan_handler(IntentId.TRANSFER_ANALYSIS.value, plan_transfer_analysis)
    register_builtin_plan_handler(IntentId.OTHER.value, plan_other)


register_builtin_plan_handlers()
