"""子进程单条评测入口：`python -m app3.eval.worker <payload.json>` 向 stdout 打印一行 JSON。

payload 支持两种格式：
1. 旧版：整对象为金标 case（`query` / `gold` / `sample_id`），等价于全图 ``invoke``。
2. 新版：`{"case": {...}, "parse_only": true|false, "include_parse_result": true|false}`，由 batch 子进程模式写入。
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from app3.config import Settings, apply_optional_env_file
from app3.eval.context_factory import build_graph_context_for_eval
from app3.eval.metrics import evaluate_case_result
from app3.nodes.parse import parse_node
from app3.runtime.session import GraphSession
from app3.state.initial_state import build_initial_state


def _default_settings_eval() -> Settings:
    apply_optional_env_file()
    s = Settings.from_env()
    return replace(s, gis_use_cache=False)


def _load_case_and_flags(path: Path) -> tuple[dict[str, Any], bool, bool]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("payload must be a JSON object")
    if "case" in raw and isinstance(raw["case"], dict):
        return (
            raw["case"],
            bool(raw.get("parse_only")),
            bool(raw.get("include_parse_result")),
        )
    return raw, False, False


def run_case_file(path: Path) -> dict[str, Any]:
    case, parse_only, include_parse_result = _load_case_and_flags(path)
    settings = _default_settings_eval()
    query = str(case.get("query") or "").strip()

    if parse_only:
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
        ev["cold_subprocess"] = True
        return ev

    session = GraphSession(settings, with_memory_checkpoint=False)
    t0 = time.perf_counter()
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
    ev["cold_subprocess"] = True
    return ev


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("usage: python -m app3.eval.worker <payload.json>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"not found: {path}", file=sys.stderr)
        return 2
    try:
        out = run_case_file(path)
    except Exception as e:  # noqa: BLE001
        err = {"worker_error": str(e), "sample_id": None}
        print(json.dumps(err, ensure_ascii=False), flush=True)
        return 1
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
