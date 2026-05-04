"""调用助手 — 用于检查点的 thread_id；从 Settings 构建 GraphContext。"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any
from uuid import uuid4

from langchain_core.tools import BaseTool

from app3.config import Settings
from app3.graph.builder import build_compiled_graph
from app3.graph.context import GraphContext
from app3.llm.errors import LLMConfigError
from app3.llm.factory import build_chat_model
from app3.skills.registry import build_default_skill_tools
from app3.state.initial_state import build_initial_state


class GraphSession:
    def __init__(
        self,
        settings: Settings,
        *,
        thread_id: str | None = None,
        tools: Sequence[BaseTool] | None = None,
    ) -> None:
        self.settings = settings
        self.thread_id = thread_id or str(uuid4())
        tool_list: Sequence[BaseTool] = tools if tools is not None else build_default_skill_tools()
        try:
            llm = build_chat_model(settings)
        except LLMConfigError:
            llm = None
        self._ctx = GraphContext(settings=settings, tools=tuple(tool_list), llm=llm)
        self._graph = build_compiled_graph(self._ctx)

    def invoke(self, user_input: str) -> dict[str, Any]:
        state = build_initial_state(user_input)
        return self._graph.invoke(
            state,
            config={"configurable": {"thread_id": self.thread_id}},
        )

    def stream(self, user_input: str) -> Iterator[dict[str, Any]]:
        state = build_initial_state(user_input)
        yield from self._graph.stream(
            state,
            config={"configurable": {"thread_id": self.thread_id}},
        )
