"""将 batch 评测结果渲染为可附在论文/实验记录后的 Markdown 报告。"""

from __future__ import annotations

import json
from typing import Any


def _bool_rate(vals: list[bool]) -> float | None:
    if not vals:
        return None
    return round(sum(1 for v in vals if v) / len(vals), 4)


def _intent_breakdown(results: list[dict[str, Any]]) -> list[tuple[str, int, float | None, float | None]]:
    """(intent, count, intent_acc, slot_acc) 按 gold.primary_intent 聚合。"""
    from collections import defaultdict

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        g = row.get("gold") if isinstance(row.get("gold"), dict) else {}
        key = str(g.get("primary_intent") or "（无）")
        buckets[key].append(row)

    out: list[tuple[str, int, float | None, float | None]] = []
    for intent in sorted(buckets.keys()):
        sub = buckets[intent]
        n = len(sub)
        iv: list[bool] = []
        sv: list[bool] = []
        for r in sub:
            chk = r.get("checks") if isinstance(r.get("checks"), dict) else {}
            if chk.get("intent_match") is not None:
                iv.append(bool(chk["intent_match"]))
            subs = [chk.get("regions_match"), chk.get("time_range_match"), chk.get("target_object_match")]
            subs_b = [bool(x) for x in subs if x is not None]
            if len(subs_b) == 3:
                sv.append(all(subs_b))
        ia = _bool_rate(iv)
        sa = _bool_rate(sv)
        out.append((intent, n, ia, sa))
    return out


def _slot_mismatch_samples(results: list[dict[str, Any]], *, limit: int = 40) -> list[dict[str, Any]]:
    """task_success 且 intent 对，但槽位未全对；或 task_success 假。"""
    picked: list[dict[str, Any]] = []
    for r in results:
        chk = r.get("checks") if isinstance(r.get("checks"), dict) else {}
        subs = [chk.get("regions_match"), chk.get("time_range_match"), chk.get("target_object_match")]
        subs_b = [bool(x) for x in subs if x is not None]
        slot_ok = len(subs_b) == 3 and all(subs_b)
        if not r.get("task_success") or not slot_ok:
            picked.append(r)
        if len(picked) >= limit:
            break
    return picked


def _component_accs(results: list[dict[str, Any]]) -> dict[str, float | None]:
    r_m: list[bool] = []
    t_m: list[bool] = []
    o_m: list[bool] = []
    for row in results:
        chk = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        if "regions_match" in chk:
            r_m.append(bool(chk["regions_match"]))
        if "time_range_match" in chk:
            t_m.append(bool(chk["time_range_match"]))
        if "target_object_match" in chk:
            o_m.append(bool(chk["target_object_match"]))
    return {
        "regions_acc": _bool_rate(r_m),
        "time_range_acc": _bool_rate(t_m),
        "target_object_acc": _bool_rate(o_m),
    }


def build_eval_report_md(
    report: dict[str, Any],
    results: list[dict[str, Any]],
) -> str:
    """生成中文实验报告正文（不含 YAML front matter）。"""
    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    comp = _component_accs(results)
    eval_mode = str(report.get("eval_mode") or "full")
    parse_only = eval_mode == "parse"
    title = (
        "# app3 小样本评测报告（仅 **parse** 节点）"
        if parse_only
        else "# app3 小样本评测报告（**端到端** LangGraph）"
    )

    lines: list[str] = [
        title,
        "",
        "## 1. 运行元数据",
        "",
        f"- **评测模式**：`{eval_mode}`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。",
        f"- **生成时间**：{report.get('generated_at', '')}",
        f"- **金标文件**：`{report.get('cases_path', '')}`",
        f"- **主意图过滤**：`{report.get('primary_intent_filter') or '（未过滤）'}`",
        f"- **样本条数**：{overall.get('case_count', len(results))}",
        f"- **GIS 任务磁盘缓存**：评测过程已强制 **`gis_use_cache=false`**（等价环境变量 `APP3_GIS_USE_CACHE=false`）。",
        f"- **完全冷启动（子进程）**：{'是 (`--cold-subprocess`)' if report.get('cold_subprocess') else '否（单进程；进程内边界/解压内存缓存仍可能存在）'}。",
        "",
        "## 2. 指标与 app3 状态字段对应",
        "",
        "| 论文/实验表述 | app3 取值来源 | 本报告计算方式 |",
        "|----------------|----------------|----------------|",
    ]

    if parse_only:
        lines.extend(
            [
                "| 解析阶段响应时间 | 仅 `parse_node` 墙钟 | 单条 `duration_ms` 的 p50 / p90 |",
                "| 解析任务成功率（技术） | `parse_result` 与 fatal | `task_success`：无 fatal 且 `queries` 非空 |",
                "| 意图 / 空间语义（主观对齐） | `parse_result.queries[0]` vs `gold` | 与全链路相同：`intent_match`、槽位三项严格相等 |",
                "",
                "> **注意**：`parse` 模式 **不执行** plan / act / explain，故不涉及 `gis_context`、`skip_gis`、GIS 流水线。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "| 系统响应时间（端到端） | `GraphSession.invoke` 墙钟 | 单条 `duration_ms` 的 p50 / p90 |",
                "| 分析任务执行成功率 | 最终 `phase`、`fatal_error`、`error_class`、`plan_result.skip_gis`、`gis_context.pipeline` | `task_success`：到达 `phase=explain` 且无 fatal；若未 `skip_gis` 则要求 `gis_context.pipeline.success==true` |",
                "| 意图识别是否准确 | `parse_result.queries[0].intent` vs `gold.primary_intent` | `intent_match`（默认要求单条子查询） |",
                "| 空间语义：行政区 / 时间 / 对象 | 同上首条 `regions`、`time_range`、`target_object` | 与金标 **列表严格字符串相等** |",
                "",
                "> 说明：行政区金标为全称时，解析若返回简称会导致 `regions_match=false`，可在附录中人工复核。",
                "",
            ]
        )

    lines.extend(
        [
            "## 3. 总体结果",
            "",
            f"- **任务成功率 `success_rate`**：{overall.get('success_rate')}"
            + ("（此处为「解析成功」占比，非端到端 GIS）" if parse_only else ""),
            f"- **意图准确率 `intent_acc`**：{overall.get('intent_acc')}",
            f"- **槽位三项合取准确率 `slot_acc`**：{overall.get('slot_acc')}",
            f"- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：{comp.get('regions_acc')}",
            f"- **时间单项 `time_range_acc`**：{comp.get('time_range_acc')}",
            f"- **对象单项 `target_object_acc`**：{comp.get('target_object_acc')}",
            f"- **响应时间 p50（ms）**：{overall.get('duration_p50_ms')}",
            f"- **响应时间 p90（ms）**：{overall.get('duration_p90_ms')}",
            "",
            "## 4. 分意图统计（按 `gold.primary_intent`）",
            "",
            "| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |",
            "|----------|-----:|-----------:|-------------------------:|",
        ]
    )

    for intent, n, ia, sa in _intent_breakdown(results):
        lines.append(
            f"| `{intent}` | {n} | {ia if ia is not None else '—'} | {sa if sa is not None else '—'} |"
        )

    lines.extend(
        [
            "",
            "## 5. 逐条结果（总表）",
            "",
            "| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |",
            "|-----------|------------:|--------------|--------------|---------|------|--------|-------|",
        ]
    )

    for r in results:
        sid = str(r.get("sample_id") or "")
        dm = r.get("duration_ms")
        ts = r.get("task_success")
        chk = r.get("checks") if isinstance(r.get("checks"), dict) else {}
        im = chk.get("intent_match")
        rm = chk.get("regions_match")
        tm = chk.get("time_range_match")
        om = chk.get("target_object_match")
        ph = str(r.get("phase") or "")
        lines.append(
            f"| {sid} | {dm if dm is not None else ''} | {ts} | {im} | {rm} | {tm} | {om} | {ph} |"
        )

    fails = [r for r in results if not r.get("task_success")]
    if fails:
        lines.extend(["", "## 6. 未通过 `task_success` 的样本", ""])
        for r in fails:
            sid = r.get("sample_id")
            lines.append(f"- **`{sid}`**：phase=`{r.get('phase')}` error_class=`{r.get('error_class')}` fatal=`{r.get('fatal_error')}` checks={json.dumps(r.get('checks'), ensure_ascii=False)}")
            gp = r.get("gis_pipeline")
            if isinstance(gp, dict) and gp:
                lines.append(f"  - **`gis_pipeline`**（GIS 摘要）：`{json.dumps(gp, ensure_ascii=False)}`")
            if r.get("subprocess_stderr"):
                lines.append(f"  - subprocess stderr 片段：`{(r.get('subprocess_stderr') or '')[:400]}`")

    mism = _slot_mismatch_samples(results, limit=50)
    if mism:
        lines.extend(
            [
                "",
                "## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）",
                "",
                "| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |",
                "|-------------|--------------|--------|---------------------|---------------------|",
            ]
        )
        for r in mism:
            sid = str(r.get("sample_id") or "")
            g = r.get("gold") if isinstance(r.get("gold"), dict) else {}
            pr = r.get("pred") if isinstance(r.get("pred"), dict) else {}
            chk = json.dumps(r.get("checks"), ensure_ascii=False)
            gr = g.get("regions")
            gt = g.get("time_range")
            prg = pr.get("regions")
            prt = pr.get("time_range")
            g_s = f"`{gr}` / `{gt}`" if isinstance(gr, list) else "—"
            p_s = f"`{prg}` / `{prt}`" if isinstance(prg, list) else "—"
            lines.append(
                f"| `{sid}` | {r.get('task_success')} | {chk} | {g_s} | {p_s} |"
            )

    lines.extend(
        [
            "",
            "## 8. 复现实验命令",
            "",
            "```bash",
            "cd <llm-agent-lab/app3>   # 含 pyproject.toml 的目录",
            "pip install -e \".[gis]\"   # 仅端到端全图时需要；只测 parse 可不装 gis",
            "# 端到端（invoke 全图）：",
            "app3-eval-paper6 --cases <path/to/cases.jsonl> --max-cases 30 \\",
            "  --primary-intent current_status_estimate",
            "# 只测 parse 节点：",
            "app3-eval-paper6 --cases <path/to/cases.jsonl> --max-cases 30 --parse-only",
            "# 完全冷启动（每条子进程）：",
            "# app3-eval-paper6 ... --cold-subprocess",
            "```",
            "",
            "## 9. 组件级分项耗时（二期）",
            "",
            "若需解析/规划/GIS 分项毫秒表：可在后续版本使用 LangGraph `stream_events`，或对 `parse_composite_query` / `build_plan_result_from_parse_dict` / 工具执行分别微基准。",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
