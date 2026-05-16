"""地图视图摘要：与 ``PlannerAgent`` 的 ``metadata`` 规则对齐（OTHER 不提示图层）。"""

from __future__ import annotations

from typing import Any

from app3.agents.planner_registry import MapInjectRole, get_map_inject_role
from app3.contracts.intents import IntentId, intent_from_str


def ui_show_polygons_from_text(text: str) -> bool:
    return any(k in text for k in ("图斑", "地图", "显示", "可视化", "展示"))


def build_map_view(parse_result: dict[str, Any] | None, user_text: str) -> dict[str, Any]:
    """
    供 LLM 规划路径写入 ``plan_result``。

    - ``other`` 意图：``show_map_layer=False``，不参与 ``map_inject_roles``。
    - ``map_inject_roles``：仅含 ``show_map_layer`` 且 ``map_role != none`` 的条目。
    - ``skip_gis``：当没有任何可展示地图子意图时为 True（与 DSL 全 other 一致）。
    """
    pr = parse_result or {}
    queries = pr.get("queries") or []
    oq_meta = (str(pr.get("original_query") or "") or "").strip()
    combined = f"{oq_meta} {user_text}".strip()
    keyword_ui = ui_show_polygons_from_text(combined)
    subplans: list[dict[str, Any]] = []
    for i, q in enumerate(queries[:3], start=1):
        intent = str(q.get("intent") or "other")
        is_other = intent_from_str(intent) == IntentId.OTHER
        role = get_map_inject_role(intent)
        show_map_layer = (not is_other) and (role != MapInjectRole.NONE)
        ui_poly = (not is_other) or keyword_ui
        subplans.append(
            {
                "index": i,
                "intent": intent,
                "map_role": role.value,
                "show_map_layer": show_map_layer,
                "ui_show_polygons": ui_poly,
            }
        )
    map_roles = [s["map_role"] for s in subplans if s["show_map_layer"]]
    skip_gis = not any(s["show_map_layer"] for s in subplans)
    return {
        "subplans": subplans,
        "map_inject_roles": map_roles,
        "skip_gis": skip_gis,
    }
