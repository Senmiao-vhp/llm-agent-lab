"""从同目录 results.jsonl 生成 error_breakdown_by_metric.md（按指标维度汇总错误与金标对照）。"""

from __future__ import annotations

import json
from pathlib import Path


def esc(s: object) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def fmt_list(x: object) -> str:
    if x is None:
        return "—"
    return json.dumps(x, ensure_ascii=False)


def task_fail_reason(r: dict) -> tuple[str, str]:
    if r.get("task_success"):
        return "", ""
    chk = r.get("checks") or {}
    keys = ("regions_match", "time_range_match", "target_object_match")
    present = [chk.get(k) for k in keys if chk.get(k) is not None]
    slots_ok = bool(present) and all(present)
    gp = r.get("gis_pipeline")
    if (r.get("phase") or "") != "explain":
        return f"phase={r.get('phase')}", esc((r.get("fatal_error") or "")[:200])
    if r.get("fatal_error"):
        return "fatal", esc(r.get("fatal_error"))[:400]
    if r.get("skip_gis"):
        return "skip_gis_task_fail", ""
    if isinstance(gp, dict) and gp.get("success") is False:
        return "gis_pipeline_fail", esc((gp.get("message") or "")[:500])
    if gp is None and not r.get("skip_gis"):
        return "gis_pipeline_absent", ""
    if chk.get("intent_match") is True and slots_ok:
        return "checks_ok_but_task_false", esc(gp)[:200]
    return "other_task_fail", esc(chk)


def main() -> None:
    here = Path(__file__).resolve().parent
    p = here / "results.jsonl"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    lines: list[str] = []
    lines.append("# 210 例评测 · 按指标类别的错误样本与金标对照")
    lines.append("")
    lines.append("数据源：本目录 `results.jsonl`（与 `eval_report.md` 同次运行）。")
    lines.append("")
    lines.append(
        "说明：按 **指标维度** 分组；同一条可出现在多个组。"
        "`other` 金标无 `regions`/`time_range` 槽位时，报告中对应检查为 `None`，不会计入 3/4 节。"
    )
    lines.append("")

    tf = [r for r in rows if not r.get("task_success")]
    lines.append("## 1. 端到端失败（`task_success = false`）")
    lines.append("")
    lines.append(f"条数：**{len(tf)}**")
    lines.append("")
    if not tf:
        lines.append("（无）")
    else:
        lines.append("| sample_id | 错误分类 | 补充 | phase | skip_gis |")
        lines.append("|-----------|----------|------|-------|----------|")
        for r in tf:
            cat, detail = task_fail_reason(r)
            lines.append(
                f"| `{r.get('sample_id')}` | {cat} | {detail} | {esc(r.get('phase'))} | {r.get('skip_gis')} |"
            )
        lines.append("")
        lines.append("### 金标 vs 预测（本组）")
        lines.append(
            "| sample_id | gold.intent | pred.intent | subq | gold.regions | pred.regions | "
            "gold.time_range | pred.time_range | gold.target | pred.target |"
        )
        lines.append(
            "|-------------|-------------|-------------|------|--------------|--------------|"
            "-----------------|----------------|-------------|-------------|"
        )
        for r in tf:
            g, pr = r.get("gold") or {}, r.get("pred") or {}
            lines.append(
                f"| `{r.get('sample_id')}` | {esc(g.get('primary_intent'))} | {esc(pr.get('intent'))} | "
                f"{pr.get('intent_subquery_count')} | {fmt_list(g.get('regions'))} | {fmt_list(pr.get('regions'))} | "
                f"{fmt_list(g.get('time_range'))} | {fmt_list(pr.get('time_range'))} | "
                f"{esc(g.get('target_object'))} | {esc(pr.get('target_object'))} |"
            )

    lines.append("")

    def add_metric_section(title: str, key: str) -> None:
        bad = [r for r in rows if (r.get("checks") or {}).get(key) is False]
        lines.append(title)
        lines.append("")
        lines.append(f"条数：**{len(bad)}**")
        lines.append("")
        if not bad:
            lines.append("（无）")
        else:
            lines.append("| sample_id | 金标 vs 预测（本项） | task_success |")
            lines.append("|-------------|----------------------|--------------|")
            for r in bad:
                g, pr = r.get("gold") or {}, r.get("pred") or {}
                if key == "intent_match":
                    cell = (
                        f"意图 金标 `{g.get('primary_intent')}` vs 预测 `{pr.get('intent')}` "
                        f"（子查询数 {pr.get('intent_subquery_count')}）"
                    )
                elif key == "regions_match":
                    cell = f"regions 金标 {fmt_list(g.get('regions'))} vs 预测 {fmt_list(pr.get('regions'))}"
                elif key == "time_range_match":
                    cell = f"time_range 金标 {fmt_list(g.get('time_range'))} vs 预测 {fmt_list(pr.get('time_range'))}"
                elif key == "target_object_match":
                    cell = f"target 金标 `{g.get('target_object')}` vs 预测 `{pr.get('target_object')}`"
                else:
                    cell = ""
                lines.append(f"| `{r.get('sample_id')}` | {cell} | {r.get('task_success')} |")
        lines.append("")

    add_metric_section("## 2. 意图不一致（`intent_match = false`）", "intent_match")
    add_metric_section("## 3. 行政区不一致（`regions_match = false`）", "regions_match")
    add_metric_section("## 4. 时间范围不一致（`time_range_match = false`）", "time_range_match")
    add_metric_section("## 5. 目标对象不一致（`target_object_match = false`）", "target_object_match")

    out = here / "error_breakdown_by_metric.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
