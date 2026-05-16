"""固定 DSL 规划器、planner_params 加载与 map 元数据单测。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app3.agents.planner_agent import (
    PlannerAgent,
    build_plan_result_from_parse_dict,
    workflow_to_plan_result,
)
from app3.agents.planner_map import build_map_view
from app3.agents.planner_params import load_planner_params
from app3.agents.planner_registry import MapInjectRole, get_map_inject_role
from app3.contracts.query import CompositeQuery, QueryIntent
from app3.errors.classify import classify_exception
from app3.errors.planner import PlannerInputError, PlannerPlanningError
from app3.errors.taxonomy import FatalSubtype, RecoverableSubtype


def test_get_map_inject_role_builtin() -> None:
    assert get_map_inject_role("change_detection") == MapInjectRole.CHANGE
    assert get_map_inject_role("current_status_estimate") == MapInjectRole.BASELINE
    assert get_map_inject_role("trend_evolution") == MapInjectRole.NONE
    assert get_map_inject_role("other") == MapInjectRole.NONE


def test_load_planner_params_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"ndvi_threshold": 0.99}), encoding="utf-8")
    monkeypatch.setenv("APP3_PLANNER_PARAMS", str(p))
    params, src = load_planner_params()
    assert src == "env"
    assert params["ndvi_threshold"] == 0.99
    assert params["search_satellite"]["max_cloud_cover"] == 20.0


def test_planner_plan_prefix_and_map_metadata() -> None:
    agent = PlannerAgent(
        params={
            "ndvi_threshold": 0.2,
            "search_satellite": {"max_cloud_cover": 20.0},
            "change_detection": {"export_geojson": True, "max_features": 5000},
            "trend": {
                "max_cloud_cover": 40.0,
                "scale_m": 200,
                "download_timeout": 360,
                "date_half_width_days": 40,
                "per_year_retries": 3,
                "retry_sleep_s": [4.0, 8.0],
            },
            "parallel": {"enabled": True, "max_workers": 4},
        }
    )
    cq = CompositeQuery(
        original_query="成都市2023年耕地变化图斑显示",
        queries=[
            QueryIntent(
                intent="change_detection",
                regions=["四川省成都市"],
                time_range=["2023"],
            )
        ],
    )
    wf = agent.plan(cq)
    assert wf["metadata"]["subplans"][0]["map_role"] == "change"
    assert wf["metadata"]["subplans"][0]["show_map_layer"] is True
    assert wf["metadata"]["subplans"][0]["ui_show_polygons"] is True
    assert wf["metadata"]["map_inject_roles"] == ["change"]
    assert wf["metadata"]["skip_gis"] is False
    tasks = wf["tasks"]
    assert tasks[0]["id"] == "q1_geom"
    detect = next(t for t in tasks if t["op"] == "detect_change")
    assert detect["params"]["export_geojson"] is True


def test_non_other_forces_export_geojson_even_if_config_off() -> None:
    agent = PlannerAgent(
        params={
            "ndvi_threshold": 0.2,
            "search_satellite": {"max_cloud_cover": 20.0},
            "change_detection": {"export_geojson": False, "max_features": 100},
            "trend": {
                "max_cloud_cover": 40.0,
                "scale_m": 200,
                "download_timeout": 360,
                "date_half_width_days": 40,
                "per_year_retries": 3,
                "retry_sleep_s": [4.0, 8.0],
            },
            "parallel": {"enabled": True, "max_workers": 4},
        }
    )
    cq = CompositeQuery(
        original_query="成都市耕地非农化情况",
        queries=[
            QueryIntent(
                intent="change_detection",
                regions=["四川省成都市"],
                time_range=["2023"],
            )
        ],
    )
    wf = agent.plan(cq)
    assert wf["metadata"]["subplans"][0]["show_map_layer"] is True
    assert wf["metadata"]["subplans"][0]["ui_show_polygons"] is True
    tasks = wf["tasks"]
    detect = next(t for t in tasks if t["op"] == "detect_change")
    assert detect["params"]["export_geojson"] is True
    baseline = next(t for t in tasks if t["id"] == "q1_baseline_mask")
    assert baseline["params"]["export_geojson"] is True


def test_build_map_view_non_other_ui_true_without_map_keywords() -> None:
    pr = {"original_query": "随便问问", "queries": [{"intent": "trend_evolution"}]}
    mv = build_map_view(pr, user_text="")
    assert mv["subplans"][0]["ui_show_polygons"] is True
    assert mv["subplans"][0]["show_map_layer"] is False
    assert mv["map_inject_roles"] == []


def test_classify_planner_exceptions() -> None:
    inp = classify_exception(PlannerInputError("bad"), source="plan_node")
    assert inp.kind == "fatal"
    assert inp.subtype == FatalSubtype.BAD_REQUEST.value
    pl = classify_exception(PlannerPlanningError("need regions"), source="plan_node")
    assert pl.kind == "recoverable"
    assert pl.subtype == RecoverableSubtype.PLANNER.value


def test_multi_region_plan_raises_planner_planning() -> None:
    agent = PlannerAgent(
        params={
            "ndvi_threshold": 0.2,
            "search_satellite": {"max_cloud_cover": 20.0},
            "change_detection": {"export_geojson": True, "max_features": 5000},
            "trend": {
                "max_cloud_cover": 40.0,
                "scale_m": 200,
                "download_timeout": 360,
                "date_half_width_days": 40,
                "per_year_retries": 3,
                "retry_sleep_s": [4.0, 8.0],
            },
            "parallel": {"enabled": True, "max_workers": 4},
        }
    )
    cq = CompositeQuery(
        original_query="对比",
        queries=[QueryIntent(intent="multi_region_compare", regions=["北京市"], time_range=[])],
    )
    with pytest.raises(PlannerPlanningError):
        agent.plan(cq)


def test_build_map_view_other_no_map_layer() -> None:
    pr = {"original_query": "你好", "queries": [{"intent": "other"}]}
    mv = build_map_view(pr, user_text="")
    assert mv["subplans"][0]["ui_show_polygons"] is False
    assert mv["subplans"][0]["show_map_layer"] is False
    assert mv["map_inject_roles"] == []
    assert mv["skip_gis"] is True
    pr2 = {"original_query": "hello", "queries": [{"intent": "other"}]}
    mv2 = build_map_view(pr2, user_text="显示地图")
    assert mv2["subplans"][0]["ui_show_polygons"] is True
    assert mv2["subplans"][0]["show_map_layer"] is False
    assert mv2["map_inject_roles"] == []


def test_workflow_to_plan_result_requires_tool() -> None:
    wf = {
        "tasks": [{"id": "x", "op": "resolve_geometry", "params": {"region": "北京市"}, "inputs": []}],
        "metadata": {},
    }
    r = workflow_to_plan_result(wf, tool_names=set())
    assert r["tool_calls"] == []
    assert "dsl_error" in r


def test_build_map_view_order() -> None:
    pr = {
        "original_query": "",
        "queries": [
            {"intent": "current_status_estimate"},
            {"intent": "change_detection"},
        ],
    }
    mv = build_map_view(pr, user_text="")
    assert [s["map_role"] for s in mv["subplans"]] == ["baseline", "change"]
    assert mv["map_inject_roles"] == ["baseline", "change"]
    assert all(s["show_map_layer"] for s in mv["subplans"])
    assert all(s["ui_show_polygons"] for s in mv["subplans"])


def test_build_plan_result_from_parse_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP3_PLANNER_PARAMS", raising=False)
    pr = {
        "original_query": "测试",
        "queries": [{"intent": "other", "regions": [], "time_range": []}],
    }
    out = build_plan_result_from_parse_dict(pr, user_text="测试", tool_names={"gis_execute_pipeline"})
    assert out["source"] == "dsl"
    assert out["workflow"]["tasks"] == []
    assert out["tool_calls"] == []
    assert out["skip_gis"] is True
    assert out["map_view"]["skip_gis"] is True
    assert out["map_view"]["map_inject_roles"] == []
