"""固定 DSL 规划器：CompositeQuery → WorkflowPlan。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app3.agents.planner_map import build_map_view, ui_show_polygons_from_text
from app3.agents.planner_params import load_planner_params
from app3.agents.planner_plugins import PlanningContext
from app3.agents.planner_registry import MapInjectRole, get_map_inject_role, get_plan_handler
from app3.agents.planner_types import TaskSpec, WorkflowPlan
from app3.contracts.intents import IntentId, intent_from_str
from app3.contracts.query import CompositeQuery
from app3.errors.planner import PlannerInputError


class PlannerAgent:
    """将解析得到的 CompositeQuery 转为带依赖的 WorkflowPlan（任务 DAG + metadata）。"""

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        """加载或注入 planner 数值参数（阈值、重试等），并记录参数来源标识。"""
        if params is None:
            self.params, self.planner_params_source = load_planner_params()
        else:
            self.params = dict(params)
            self.planner_params_source = "injected"

    def plan(self, composite_query: CompositeQuery | dict[str, Any]) -> dict[str, Any]:
        """按子查询（最多 3 条）调用意图处理器生成 TaskSpec；组装 subplans、地图角色与 skip_gis。"""
        if isinstance(composite_query, dict):
            try:
                composite_query = CompositeQuery.model_validate(composite_query)
            except ValidationError as e:
                raise PlannerInputError(f"CompositeQuery 无效: {e}") from e
        if not composite_query.queries:
            raise PlannerInputError("No sub-queries produced by parser.")
        oq = (getattr(composite_query, "original_query", "") or "").strip()
        keyword_ui = ui_show_polygons_from_text(oq)

        tasks_all: list[TaskSpec] = []
        subplans: list[dict[str, Any]] = []

        for i, qi in enumerate(composite_query.queries[:3], start=1):
            role = get_map_inject_role(qi.intent)
            is_other = intent_from_str(qi.intent) == IntentId.OTHER
            ui_poly = (not is_other) or keyword_ui
            ctx = PlanningContext(params=self.params, ui_show_polygons=ui_poly)
            handler = get_plan_handler(qi.intent)
            tasks = handler(ctx, qi)
            has_tasks = len(tasks) > 0
            show_map_layer = (not is_other) and has_tasks and (role != MapInjectRole.NONE)

            base_sp: dict[str, Any] = {
                "index": i,
                "intent": qi.intent,
                "region": qi.regions[0] if qi.regions else None,
                "regions": list(qi.regions),
                "time_range": list(qi.time_range),
                "target_object": qi.target_object,
                "task_prefix": f"q{i}_",
                "map_role": role.value,
                "show_map_layer": show_map_layer,
                "ui_show_polygons": ui_poly,
            }

            if not tasks:
                base_sp["final_task_id"] = None
                subplans.append(base_sp)
                continue

            prefix = f"q{i}_"
            tasks_pref, final_id = self._prefix_tasks(tasks, prefix)
            tasks_all.extend(tasks_pref)
            base_sp["final_task_id"] = final_id
            subplans.append(base_sp)

        map_roles_f = [str(sp["map_role"]) for sp in subplans if sp.get("show_map_layer")]
        skip_gis = len(tasks_all) == 0

        meta: dict[str, Any] = {
            "intents": [sp["intent"] for sp in subplans],
            "subplans": subplans,
            "map_inject_roles": map_roles_f,
            "skip_gis": skip_gis,
            "planner_params_source": self.planner_params_source,
        }

        if not tasks_all:
            return {"tasks": [], "metadata": meta}

        return WorkflowPlan(tasks=tasks_all, metadata=meta).model_dump()

    @staticmethod
    def _prefix_tasks(tasks: list[TaskSpec], prefix: str) -> tuple[list[TaskSpec], str]:
        """为子查询任务 id / 输入引用加上前缀，避免多子查询间 id 冲突；返回重命名后的任务列表与末任务 id。"""
        out: list[TaskSpec] = []
        id_map: dict[str, str] = {}
        for t in tasks:
            id_map[t.id] = prefix + t.id
        for t in tasks:
            new_inputs: list[str] = []
            for ref in t.inputs:
                if isinstance(ref, str) and ref.startswith("$") and ref.endswith(".output"):
                    old = ref[1 : -len(".output")]
                    new_inputs.append(f"${id_map.get(old, old)}.output")
                else:
                    new_inputs.append(ref)
            out.append(
                TaskSpec(
                    id=id_map[t.id],
                    op=t.op,
                    params=t.params,
                    inputs=new_inputs,
                )
            )
        final_id = id_map[tasks[-1].id]
        return out, final_id


def workflow_to_plan_result(
    workflow: dict[str, Any],
    *,
    tool_names: set[str],
) -> dict[str, Any]:
    """把 WorkflowPlan 字典转成 act 可用的 plan_result 雏形：tool_calls、skip_gis、可选 dsl_error。"""
    tasks = workflow.get("tasks") or []
    meta = workflow.get("metadata") if isinstance(workflow.get("metadata"), dict) else {}
    out: dict[str, Any] = {
        "workflow": workflow,
        "tool_calls": [],
        "content": "固定 DSL 规划：已生成 GIS 工作流（metadata 含 map_role / subplans）。",
        "skip_gis": bool(meta.get("skip_gis", not tasks)),
    }
    if not tasks:
        return out
    if "gis_execute_pipeline" not in tool_names:
        out["dsl_error"] = (
            "工作流含任务但当前未注册 gis_execute_pipeline 工具（可能未安装 [gis] extras）。"
        )
        return out
    try:
        dsl_json = json.dumps(workflow, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        out["dsl_error"] = f"无法序列化工作流 DSL: {e}"
        return out
    out["tool_calls"] = [
        {"name": "gis_execute_pipeline", "args": {"dsl_json": dsl_json}, "id": "plan_dsl"},
    ]
    return out


def build_plan_result_from_parse_dict(
    parse_result: dict[str, Any],
    *,
    user_text: str,
    tool_names: set[str],
    planner: PlannerAgent | None = None,
) -> dict[str, Any]:
    """从 parse 结果跑 DSL 规划，合并 workflow、map_view 与顶层 skip_gis，供 plan 节点写入 state。"""
    agent = planner or PlannerAgent()
    wf = agent.plan(parse_result)
    pr = workflow_to_plan_result(wf, tool_names=tool_names)
    pr["source"] = "dsl"
    mv = build_map_view(parse_result, user_text)
    pr["map_view"] = mv
    meta = wf.get("metadata") if isinstance(wf.get("metadata"), dict) else {}
    pr["skip_gis"] = bool(meta.get("skip_gis", pr.get("skip_gis")))
    return pr
