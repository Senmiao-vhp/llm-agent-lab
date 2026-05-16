"""调用助手 — 用于检查点的 thread_id；从 Settings 构建 GraphContext。"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any
from uuid import uuid4

from langchain_core.tools import BaseTool

from app3.config import Settings
from app3.graph.builder import build_compiled_graph
from app3.graph.context import GraphContext
from app3.kg.neo4j_client import build_neo4j_client_from_settings
from app3.llm.errors import LLMConfigError
from app3.llm.factory import build_chat_model
from app3.skills.registry import build_default_skill_tools
from app3.state.initial_state import build_initial_state


class GraphSession:
    """一次可复用的图运行会话：持有 GraphContext、编译图与 thread_id，用于 invoke/stream。"""

    def __init__(
        self,
        settings: Settings,
        *,
        thread_id: str | None = None,
        tools: Sequence[BaseTool] | None = None,
        with_memory_checkpoint: bool = True,
    ) -> None:
        """根据 Settings 装配 Neo4j 客户端、工具列表、可选 LLM 与 GraphContext，并编译 LangGraph。

        ``with_memory_checkpoint=False``：不挂 MemorySaver，适合批量评测（state 中可能含不可序列化对象）。
        """
        self.settings = settings
        self.thread_id = thread_id or str(uuid4())
        neo_client = build_neo4j_client_from_settings(settings)
        tool_list: Sequence[BaseTool] = (
            tools
            if tools is not None
            else build_default_skill_tools(settings, neo4j_client=neo_client)
        )
        try:
            llm = build_chat_model(settings)
        except LLMConfigError:
            llm = None
        self._ctx = GraphContext(
            settings=settings,
            tools=tuple(tool_list),
            llm=llm,
            neo4j_client=neo_client,
        )
        self._graph = build_compiled_graph(self._ctx, with_memory_checkpoint=with_memory_checkpoint)

    def close(self) -> None:
        """释放 Neo4j Driver 等长生命周期资源。"""
        client = self._ctx.neo4j_client
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass

    def invoke(self, user_input: str) -> dict[str, Any]:
        """从用户输入构造初始 state，同步跑完整图并返回最终 state 字典。"""
        state = build_initial_state(user_input)
        return self._graph.invoke(
            state,
            config={"configurable": {"thread_id": self.thread_id}},
        )

    def stream(self, user_input: str) -> Iterator[dict[str, Any]]:
        """与 invoke 相同入口，但以 LangGraph stream 迭代各步更新（便于 UI 增量展示）。"""
        state = build_initial_state(user_input)
        yield from self._graph.stream(
            state,
            config={"configurable": {"thread_id": self.thread_id}},
        )
