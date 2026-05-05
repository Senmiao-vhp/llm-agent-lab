"""编译时图依赖（注入式；避免隐藏全局变量）。"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app3.config import Settings

if TYPE_CHECKING:
    from app3.kg.neo4j_client import Neo4jClient


@dataclass(frozen=True)
class GraphContext:
    """节点从外部状态需要的所有内容 — 每个编译的图只构建一次。"""

    settings: Settings
    tools: tuple[BaseTool, ...]
    llm: BaseChatModel | None
    neo4j_client: Neo4jClient | None = None
