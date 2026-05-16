"""批量跑 JSONL 金标（论文第六章 app3 小样本）；支持 `--cold-subprocess` 完全冷启动。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from app3.config import Settings, apply_optional_env_file
from app3.eval.context_factory import build_graph_context_for_eval
from app3.eval.metrics import aggregate, evaluate_case_result
from app3.eval.report_md import build_eval_report_md
from app3.nodes.parse import parse_node
from app3.runtime.session import GraphSession
from app3.state.initial_state import build_initial_state


def _project_root() -> Path:
    """…/llm-agent-lab/app3（含 pyproject.toml）。"""
    return Path(__file__).resolve().parents[2]


def _default_cases_path() -> Path | None:
    """优先 `data/eval_cases_210.jsonl`，其次旧版 `paper6_cases.jsonl`，再尝试 monorepo 的 farmland-monitoring。"""
    root = _project_root()
    p210 = root / "data" / "eval_cases_210.jsonl"
    if p210.is_file():
        return p210
    paper6 = root / "data" / "paper6_cases.jsonl"
    if paper6.is_file():
        return paper6
    lab = root.parent
    candidate = lab.parent / "farmland-monitoring" / "data" / "eval_runs" / "cases.jsonl"
    return candidate if candidate.is_file() else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = (line or "").strip()
            if not s or s.startswith("#"):
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _filter_cases(
    rows: list[dict[str, Any]],
    *,
    primary_intent: str | None,
    max_cases: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        if primary_intent:
            g = r.get("gold") if isinstance(r.get("gold"), dict) else {}
            if str(g.get("primary_intent") or "") != primary_intent:
                continue
        out.append(r)
        if len(out) >= max_cases:
            break
    return out


def _cases_by_sample_ids(rows: list[dict[str, Any]], wanted_ids: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """按 ``wanted_ids`` 顺序取用例；返回 (cases, missing_ids)。"""
    by_sid: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = r.get("sample_id")
        if sid is None:
            continue
        by_sid[str(sid)] = r
    cases: list[dict[str, Any]] = []
    missing: list[str] = []
    for sid in wanted_ids:
        row = by_sid.get(sid)
        if row is not None:
            cases.append(row)
        else:
            missing.append(sid)
    return cases, missing


def _worker_envelope(
    case: dict[str, Any],
    *,
    parse_only: bool,
    include_parse_result: bool = False,
) -> dict[str, Any]:
    return {
        "case": case,
        "parse_only": bool(parse_only),
        "include_parse_result": bool(include_parse_result),
    }


def _run_parse_only_in_process(
    case: dict[str, Any],
    settings: Settings,
    *,
    include_parse_result: bool = False,
) -> dict[str, Any]:
    query = str(case.get("query") or "").strip()
    ctx = build_graph_context_for_eval(settings)
    state = build_initial_state(query)
    t0 = time.perf_counter()
    try:
        patch = parse_node(state, ctx=ctx)
    finally:
        if ctx.neo4j_client is not None:
            try:
                ctx.neo4j_client.close()
            except Exception:  # noqa: BLE001
                pass
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    final = {**state, **patch}
    ev = evaluate_case_result(
        case,
        final,
        eval_mode="parse",
        include_parse_result=include_parse_result,
    )
    ev["duration_ms"] = round(elapsed_ms, 3)
    ev["cold_subprocess"] = False
    return ev


def _run_in_process(
    case: dict[str, Any],
    settings: Settings,
    *,
    include_parse_result: bool = False,
) -> dict[str, Any]:
    query = str(case.get("query") or "").strip()
    t0 = time.perf_counter()
    session = GraphSession(settings, with_memory_checkpoint=False)
    try:
        final = session.invoke(query)
    finally:
        session.close()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    ev = evaluate_case_result(
        case,
        final if isinstance(final, dict) else {},
        eval_mode="full",
        include_parse_result=include_parse_result,
    )
    ev["duration_ms"] = round(elapsed_ms, 3)
    ev["cold_subprocess"] = False
    return ev


def _run_subprocess(
    case: dict[str, Any],
    *,
    python_exe: str,
    parse_only: bool,
    include_parse_result: bool = False,
) -> dict[str, Any]:
    root = _project_root()
    env = os.environ.copy()
    env["APP3_GIS_USE_CACHE"] = "false"
    env.setdefault("PYTHONUTF8", "1")
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(
            _worker_envelope(
                case,
                parse_only=parse_only,
                include_parse_result=include_parse_result,
            ),
            tmp,
            ensure_ascii=False,
        )
        tmp_path = tmp.name
    try:
        cmd = [python_exe, "-m", "app3.eval.worker", tmp_path]
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=7200,
        )
        if proc.returncode != 0:
            return {
                "sample_id": case.get("sample_id"),
                "query": case.get("query"),
                "task_success": False,
                "duration_ms": None,
                "checks": {},
                "subprocess_stderr": (proc.stderr or "")[:2000],
                "subprocess_stdout_tail": (proc.stdout or "")[-1500:] if proc.stdout else "",
                "subprocess_returncode": proc.returncode,
            }
        line = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else ""
        try:
            return json.loads(line) if line else {}
        except json.JSONDecodeError:
            return {
                "sample_id": case.get("sample_id"),
                "query": case.get("query"),
                "task_success": False,
                "duration_ms": None,
                "checks": {},
                "subprocess_stdout_tail": (proc.stdout or "")[-2000:],
                "subprocess_stderr": (proc.stderr or "")[:2000],
                "parse_error": "worker stdout is not valid JSON",
            }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Paper Ch.6 app3 batch eval (JSONL gold cases).")
    parser.add_argument(
        "--cases",
        type=str,
        default="",
        help="Path to cases.jsonl (default: sibling farmland-monitoring/.../cases.jsonl if present)",
    )
    parser.add_argument(
        "--primary-intent",
        type=str,
        default="current_status_estimate",
        help="只保留 gold.primary_intent 等于该值的用例（默认 current_status_estimate）。与 --no-intent-filter 互斥。",
    )
    parser.add_argument(
        "--no-intent-filter",
        action="store_true",
        help="不按 primary_intent 过滤（用于混合意图金标；配合 --max-cases）",
    )
    parser.add_argument("--max-cases", type=int, default=30, help="Max cases after filter (default 30)")
    parser.add_argument(
        "--max-per-intent",
        type=int,
        default=0,
        help="与 --no-intent-filter 合用：按文件顺序，每种 gold.primary_intent 至多保留前 N 条（0 表示关闭）。",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="--cold-subprocess 时子进程使用的 Python 可执行文件（默认当前解释器）",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Output directory (default: app3/data/eval_runs/eval_TIMESTAMP)",
    )
    parser.add_argument(
        "--cold-subprocess",
        action="store_true",
        help="Each case in a fresh Python process (完全冷启动，避免进程内 GIS 内存缓存)",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="只评测 parse 节点（parse_node），不跑 plan/act/explain；无需 GEE/GIS 全链路",
    )
    parser.add_argument(
        "--sample-ids",
        type=str,
        default="",
        help="逗号分隔的 sample_id 列表；若指定则只跑这些用例（顺序与列表一致），并忽略 --primary-intent / --max-cases / --max-per-intent",
    )
    parser.add_argument(
        "--include-parse-result",
        action="store_true",
        help="在 results.jsonl 每条记录中附加完整 parse_result（含 queries 内 _time_refinement 等调试字段）",
    )
    args = parser.parse_args(argv)

    cases_path = Path(args.cases) if args.cases else None
    if not cases_path:
        d = _default_cases_path()
        cases_path = d
    if cases_path is None or not cases_path.is_file():
        print("cases.jsonl not found: pass --cases", file=sys.stderr)
        return 2

    apply_optional_env_file()
    settings = replace(Settings.from_env(), gis_use_cache=False)

    rows = _read_jsonl(cases_path)
    intent_f = None if args.no_intent_filter else ((args.primary_intent or "").strip() or None)
    per_i = max(0, int(args.max_per_intent))
    sample_ids_arg = (args.sample_ids or "").strip()
    if sample_ids_arg:
        wanted = [x.strip() for x in sample_ids_arg.split(",") if x.strip()]
        cases, missing = _cases_by_sample_ids(rows, wanted)
        if missing:
            print(f"Warning: sample_ids not in cases file: {missing}", file=sys.stderr)
    elif per_i > 0:
        if not args.no_intent_filter:
            print("--max-per-intent 需要同时传入 --no-intent-filter", file=sys.stderr)
            return 2
        cases = []
        seen: dict[str, int] = {}
        for r in rows:
            g = r.get("gold") if isinstance(r.get("gold"), dict) else {}
            ik = str(g.get("primary_intent") or "")
            n = seen.get(ik, 0)
            if n >= per_i:
                continue
            seen[ik] = n + 1
            cases.append(r)
    else:
        cases = _filter_cases(rows, primary_intent=intent_f, max_cases=max(1, int(args.max_cases)))
    if not cases:
        print("No cases matched filter.", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = _project_root()
    out_dir = Path(args.out_dir) if args.out_dir else out_root / "data" / "eval_runs" / f"eval_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    inc_pr = bool(args.include_parse_result)
    results: list[dict[str, Any]] = []
    for i, case in enumerate(cases, start=1):
        sid = case.get("sample_id") or f"case_{i}"
        print(f"[{i}/{len(cases)}] {sid} …", flush=True)
        if args.cold_subprocess:
            ev = _run_subprocess(
                case,
                python_exe=str(args.python),
                parse_only=bool(args.parse_only),
                include_parse_result=inc_pr,
            )
        elif args.parse_only:
            ev = _run_parse_only_in_process(case, settings, include_parse_result=inc_pr)
        else:
            ev = _run_in_process(case, settings, include_parse_result=inc_pr)
        results.append(ev)

    overall = aggregate(results)
    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "cases_path": str(cases_path.resolve()),
        "primary_intent_filter": None if sample_ids_arg else intent_f,
        "max_per_intent": per_i if per_i > 0 else None,
        "max_cases": len(cases),
        "sample_ids_filter": [x.strip() for x in sample_ids_arg.split(",") if x.strip()] if sample_ids_arg else None,
        "include_parse_result": inc_pr,
        "cold_subprocess": bool(args.cold_subprocess),
        "gis_use_cache": False,
        "eval_mode": "parse" if args.parse_only else "full",
        "overall": overall,
    }
    with open(out_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(out_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report_md = build_eval_report_md(report, results)
    (out_dir / "eval_report.md").write_text(report_md, encoding="utf-8")
    summary_lines = [
        "# App3 eval（摘要）",
        "",
        f"- 完整报告见同目录 **`eval_report.md`**",
        f"- eval_mode: {report.get('eval_mode', 'full')}",
        f"- cases: {overall.get('case_count')}",
        f"- success_rate: {overall.get('success_rate')}",
        f"- intent_acc: {overall.get('intent_acc')}",
        f"- slot_acc: {overall.get('slot_acc')}",
        f"- duration_p50_ms: {overall.get('duration_p50_ms')}",
        f"- duration_p90_ms: {overall.get('duration_p90_ms')}",
        "",
        f"Output: {out_dir}",
    ]
    (out_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Done. {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
