"""使用注入的 GraphContext 组装 StateGraph 并连接条件边。"""

from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app3.graph import edges
from app3.graph.checkpointing import build_memory_checkpointer
from app3.graph.constants import NodeName, RouteKey
from app3.graph.context import GraphContext
from app3.nodes.act import act_node
from app3.nodes.delay import delay_node
from app3.nodes.errors import handle_error_node
from app3.nodes.explain import explain_node
from app3.nodes.parse import parse_node
from app3.nodes.plan import plan_node
from app3.state.agent_state import AgentState


def build_compiled_graph(
    ctx: GraphContext,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    with_memory_checkpoint: bool = True,
) -> Any:
    """返回编译后的图；`Any` 类型可防止 LangGraph 升级破坏类型检查。

    GIS 等节点可能在 state 中放入不可 msgpack 序列化的对象（如 rasterio Profile），
    批量评测时应设 ``with_memory_checkpoint=False``，避免 MemorySaver 写检查点失败。
    """
    g = StateGraph(AgentState)

    g.add_node(NodeName.PARSE, partial(parse_node, ctx=ctx))
    g.add_node(NodeName.PLAN, partial(plan_node, ctx=ctx))
    g.add_node(NodeName.ACT, partial(act_node, ctx=ctx))
    g.add_node(NodeName.EXPLAIN, partial(explain_node, ctx=ctx))
    g.add_node(NodeName.HANDLE_ERROR, partial(handle_error_node, ctx=ctx))
    g.add_node(NodeName.DELAY, partial(delay_node, ctx=ctx))

    g.add_edge(START, NodeName.PARSE)

    g.add_conditional_edges(
        NodeName.PARSE,
        edges.route_after_parse,
        {RouteKey.PLAN: NodeName.PLAN, RouteKey.END: END},
    )
    g.add_conditional_edges(
        NodeName.PLAN,
        edges.route_after_plan,
        {RouteKey.ACT: NodeName.ACT, RouteKey.END: END},
    )
    g.add_conditional_edges(
        NodeName.ACT,
        edges.route_after_act,
        {
            RouteKey.EXPLAIN: NodeName.EXPLAIN,
            NodeName.HANDLE_ERROR: NodeName.HANDLE_ERROR,
            RouteKey.END: END,
        },
    )
    g.add_edge(NodeName.EXPLAIN, END)

    g.add_conditional_edges(
        NodeName.HANDLE_ERROR,
        edges.route_after_handle_error,
        {
            RouteKey.DELAY: NodeName.DELAY,
            RouteKey.PLAN: NodeName.PLAN,
            RouteKey.END: END,
        },
    )
    g.add_edge(NodeName.DELAY, NodeName.PLAN)

    if not with_memory_checkpoint:
        return g.compile()
    cp = checkpointer or build_memory_checkpointer()
    return g.compile(checkpointer=cp)
