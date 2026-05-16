"""内置意图 → 规划函数注册表；地图注入角色（无管理员自定义覆盖）。"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Callable, Dict, List

from app3.contracts.intents import IntentId, intent_from_str

if TYPE_CHECKING:
    from app3.agents.planner_plugins import PlanningContext
    from app3.agents.planner_types import TaskSpec
    from app3.contracts.query import QueryIntent

IntentPlanFn = Callable[["PlanningContext", "QueryIntent"], List["TaskSpec"]]

BUILTIN_PLAN_HANDLER_BY_INTENT: Dict[str, IntentPlanFn] = {}


def register_builtin_plan_handler(intent: str | IntentId, handler: IntentPlanFn) -> None:
    BUILTIN_PLAN_HANDLER_BY_INTENT[str(intent)] = handler


def get_plan_handler(intent: str | IntentId) -> IntentPlanFn:
    i = intent_from_str(str(intent))
    if i.value in BUILTIN_PLAN_HANDLER_BY_INTENT:
        return BUILTIN_PLAN_HANDLER_BY_INTENT[i.value]
    return BUILTIN_PLAN_HANDLER_BY_INTENT[IntentId.OTHER.value]


class MapInjectRole(StrEnum):
    NONE = "none"
    CHANGE = "change"
    BASELINE = "baseline"


INTENT_MAP_ROLE: Dict[IntentId, MapInjectRole] = {
    IntentId.CHANGE_DETECTION: MapInjectRole.CHANGE,
    IntentId.CURRENT_STATUS_ESTIMATE: MapInjectRole.BASELINE,
}


def get_map_inject_role(intent: str | IntentId) -> MapInjectRole:
    """仅内置意图表（不读自定义 intents JSON）。"""
    return INTENT_MAP_ROLE.get(intent_from_str(str(intent)), MapInjectRole.NONE)
