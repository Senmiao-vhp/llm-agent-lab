"""阻塞式退避 — 生产环境可换异步或外部调度。"""

from __future__ import annotations

import time

from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState


def delay_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    t = float(state.get("pending_sleep_seconds") or 0.0)
    cap = float(ctx.settings.backoff_max_seconds)
    t = max(0.0, min(t, cap))
    if t > 0:
        time.sleep(t)
    return {"pending_sleep_seconds": 0.0, "phase": "delay"}
