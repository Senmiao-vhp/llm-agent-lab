"""评测与脚本复用：从 Settings 构建 GraphContext（与 GraphSession 装配一致）。"""

from __future__ import annotations

from app3.config import Settings
from app3.graph.context import GraphContext
from app3.kg.neo4j_client import build_neo4j_client_from_settings
from app3.llm.errors import LLMConfigError
from app3.llm.factory import build_chat_model
from app3.skills.registry import build_default_skill_tools


def build_graph_context_for_eval(settings: Settings) -> GraphContext:
    neo_client = build_neo4j_client_from_settings(settings)
    tools = tuple(build_default_skill_tools(settings, neo4j_client=neo_client))
    try:
        llm = build_chat_model(settings)
    except LLMConfigError:
        llm = None
    return GraphContext(
        settings=settings,
        tools=tools,
        llm=llm,
        neo4j_client=neo_client,
    )
