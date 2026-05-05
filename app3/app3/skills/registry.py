"""中心工具注册表，用于将工具传递给 GraphContext。"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from app3.config import Settings
from app3.kg.neo4j_client import Neo4jClient, build_neo4j_client_from_settings
from app3.kg.tools import build_graphrag_tools, build_neo4j_tools
from app3.skills.gis.tools import build_gis_placeholder_tools


def build_default_skill_tools(
    settings: Settings,
    *,
    neo4j_client: Neo4jClient | None = None,
) -> Sequence[BaseTool]:
    """若传入同一 Neo4jClient 实例，可与 GraphContext 共用 Driver，避免重复连接。"""
    client = neo4j_client if neo4j_client is not None else build_neo4j_client_from_settings(settings)
    return [
        *build_gis_placeholder_tools(),
        *build_neo4j_tools(client),
        *build_graphrag_tools(settings, neo4j_client=client),
    ]
