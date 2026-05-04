"""阻塞式退避 — 生产环境可换异步或外部调度。"""

from __future__ import annotations

import os
import time

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState


def delay_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    _ = ctx
    t = float(state.get("pending_sleep_seconds") or 0.0)
    cap = float(os.getenv("APP3_BACKOFF_MAX_SECONDS", "120") or 120)
    t = max(0.0, min(t, cap))
    if t > 0:
        time.sleep(t)
    return {"pending_sleep_seconds": 0.0, "phase": "delay"}
