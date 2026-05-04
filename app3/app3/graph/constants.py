"""图节点名称和路由键的单一事实来源（path_map）。"""

from __future__ import annotations


class NodeName:
    """已注册的 `StateGraph.add_node` 名称 — 必须与路由返回值匹配。"""

    PARSE = "parse"
    PLAN = "plan"
    ACT = "act"
    EXPLAIN = "explain"
    HANDLE_ERROR = "handle_error"
    DELAY = "delay"


class RouteKey:
    """
    `edges.route_*` 函数的返回值。
    值必须与 `add_conditional_edges(..., path_map)` 键匹配。
    """

    PLAN = "plan"
    ACT = "act"
    EXPLAIN = "explain"
    HANDLE_ERROR = "handle_error"
    DELAY = "delay"
    END = "end"
