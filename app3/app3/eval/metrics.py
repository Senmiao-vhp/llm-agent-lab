"""单条用例：最终 state 与 gold 对齐；任务成功判据（与第六章指标对应）。"""

from __future__ import annotations

from typing import Any, Literal


def _first_query_dict(parse_result: dict[str, Any]) -> dict[str, Any]:
    qs = parse_result.get("queries")
    if not isinstance(qs, list) or not qs or not isinstance(qs[0], dict):
        return {}
    return qs[0]


def _intent_subquery_count(parse_result: dict[str, Any]) -> int:
    qs = parse_result.get("queries")
    if not isinstance(qs, list):
        return 0
    return sum(1 for q in qs if isinstance(q, dict))


def evaluate_case_result(
    case: dict[str, Any],
    final_state: dict[str, Any],
    *,
    eval_mode: Literal["full", "parse"] = "full",
    include_parse_result: bool = False,
) -> dict[str, Any]:
    """
    从 state 与 case.gold 构造 checks 与 task_success。

    - ``full``：整图跑完；``task_success`` = 无 fatal、``phase=explain``；未 ``skip_gis`` 时需 pipeline.success。
    - ``parse``：仅解析节点；``task_success`` = 无 fatal 且 ``parse_result.queries`` 非空（不测 GIS/plan）。
    - ``include_parse_result``：为 True 时在返回 dict 中附加 ``parse_result`` 全量（用于调试时间精炼等）。
    """
    gold = case.get("gold") if isinstance(case.get("gold"), dict) else {}
    gold_pi = str(gold.get("primary_intent") or "")

    pr = final_state.get("parse_result") if isinstance(final_state.get("parse_result"), dict) else {}
    first = _first_query_dict(pr)
    pred_intent = first.get("intent")
    pred_intent_s = str(pred_intent) if pred_intent is not None else None
    pred_regions = first.get("regions") if isinstance(first.get("regions"), list) else []
    pred_time = first.get("time_range") if isinstance(first.get("time_range"), list) else []
    pred_target = first.get("target_object")

    checks: dict[str, bool | None] = {
        "intent_match": None,
        "regions_match": None,
        "time_range_match": None,
        "target_object_match": None,
    }

    if gold_pi:
        base = gold_pi == pred_intent_s
        subq_n = _intent_subquery_count(pr)
        relax_multi = gold.get("allow_multi_query") is True or gold_pi == "multi_region_compare"
        checks["intent_match"] = bool(base) if relax_multi else bool(base and subq_n <= 1)

    if gold_pi != "other":
        gr = gold.get("regions")
        if isinstance(gr, list):
            checks["regions_match"] = [str(x) for x in gr] == [str(x) for x in pred_regions]
        gt = gold.get("time_range")
        if isinstance(gt, list):
            checks["time_range_match"] = [str(x) for x in gt] == [str(x) for x in pred_time]
        go = gold.get("target_object")
        if go is not None:
            checks["target_object_match"] = str(go) == str(pred_target)

    plan = final_state.get("plan_result") if isinstance(final_state.get("plan_result"), dict) else {}
    skip_gis = bool(plan.get("skip_gis"))

    gis = final_state.get("gis_context")
    pipeline_ok = True
    if not skip_gis:
        if isinstance(gis, dict) and isinstance(gis.get("pipeline"), dict):
            pipeline_ok = bool(gis["pipeline"].get("success") is True)
        else:
            pipeline_ok = False

    fatal = (final_state.get("fatal_error") or "").strip()
    ec = str(final_state.get("error_class") or "none")
    phase = str(final_state.get("phase") or "")
    no_fatal = not fatal and ec != "fatal"

    if eval_mode == "parse":
        pr_ok = isinstance(pr, dict) and isinstance(pr.get("queries"), list) and len(pr["queries"]) > 0
        task_success = bool(no_fatal and pr_ok)
    else:
        phase_ok = phase == "explain"
        task_success = bool(no_fatal and phase_ok and (pipeline_ok if not skip_gis else True))

    gis_pipeline_out: dict[str, Any] | None = None
    if eval_mode == "full" and isinstance(gis, dict):
        pipe = gis.get("pipeline")
        if isinstance(pipe, dict):
            # 与 act 节点写入字段一致；仅保留可 JSON 落盘的标量（避免意外不可序列化对象）
            gis_pipeline_out = {}
            for k in ("success", "message", "final_type", "error", "code"):
                if k in pipe:
                    gis_pipeline_out[k] = pipe[k]

    out: dict[str, Any] = {
        "sample_id": case.get("sample_id"),
        "query": case.get("query"),
        "gold": gold,
        "pred": {
            "intent": pred_intent_s,
            "intent_subquery_count": _intent_subquery_count(pr),
            "regions": pred_regions,
            "time_range": pred_time,
            "target_object": pred_target,
        },
        "checks": {k: v for k, v in checks.items() if v is not None},
        "task_success": task_success,
        "skip_gis": skip_gis,
        "phase": phase,
        "fatal_error": fatal or None,
        "error_class": ec,
        "eval_mode": eval_mode,
    }
    if eval_mode == "full":
        out["gis_pipeline"] = gis_pipeline_out
    if include_parse_result and isinstance(pr, dict) and pr:
        out["parse_result"] = pr
    return out


def bool_rate(vals: list[bool]) -> float | None:
    if not vals:
        return None
    return round(sum(1 for v in vals if v) / len(vals), 4)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    rank = max(0.0, min(1.0, p)) * (len(xs) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(xs) - 1)
    frac = rank - lo
    return round(xs[lo] * (1.0 - frac) + xs[hi] * frac, 3)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """与论文第六章对应的 overall 汇总。"""
    success_vals: list[bool] = []
    intent_vals: list[bool] = []
    slot_vals: list[bool] = []
    durations: list[float] = []

    for r in rows:
        success_vals.append(bool(r.get("task_success")))
        chk = r.get("checks") if isinstance(r.get("checks"), dict) else {}
        if chk.get("intent_match") is not None:
            intent_vals.append(bool(chk["intent_match"]))
        subs = [chk.get("regions_match"), chk.get("time_range_match"), chk.get("target_object_match")]
        subs_b = [bool(x) for x in subs if x is not None]
        if len(subs_b) == 3:
            slot_vals.append(all(subs_b))
        dm = r.get("duration_ms")
        if dm is not None:
            try:
                durations.append(float(dm))
            except (TypeError, ValueError):
                pass

    overall: dict[str, Any] = {
        "case_count": len(rows),
        "success_rate": bool_rate(success_vals) or 0.0,
        "intent_acc": bool_rate(intent_vals),
        "slot_acc": bool_rate(slot_vals),
        "duration_p50_ms": percentile(durations, 0.5) if durations else 0.0,
        "duration_p90_ms": percentile(durations, 0.9) if durations else 0.0,
    }
    return overall
