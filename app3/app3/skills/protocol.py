"""技能 = LangChain StructuredTool；用于可选工具的注册表元数据。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.tools import StructuredTool


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    args_schema: type[Any]
    sync_fn: Callable[..., Any] | None = None

    def to_structured_tool(self) -> StructuredTool:
        if self.sync_fn is None:
            raise ValueError("sync_fn is required for SkillDefinition.to_structured_tool")
        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
            func=self.sync_fn,
        )
