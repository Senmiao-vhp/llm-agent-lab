"""CLI 入口（最小化实现）。"""

from __future__ import annotations

import argparse
import json

from app3.config import Settings
from app3.runtime.session import GraphSession


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app3", description="LangGraph learning agent.")
    parser.add_argument("query", nargs="?", default="ping", help="User message.")
    parser.add_argument("--thread-id", default=None, help="Optional LangGraph thread_id.")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    session = GraphSession(settings, thread_id=args.thread_id)
    out = session.invoke(args.query)
    print(json.dumps({k: out[k] for k in out if k != "messages"}, ensure_ascii=False, indent=2))
    return 0
