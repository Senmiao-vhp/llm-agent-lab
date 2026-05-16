"""形态 A：Neo4j 只读 Tools；形态 C：GraphRAG Tool（向量检索 + 子图扩展）。"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app3.config import Settings
from app3.kg.graphrag import graphrag_retrieve
from app3.kg.neo4j_client import Neo4jClient


class ResolveRegionArgs(BaseModel):
    query_text: str = Field(description="地名或行政区标识符片段或完整 region_id。")
    limit: int = Field(default=10, ge=1, le=50)


class OperatorDepsArgs(BaseModel):
    operator_name: str = Field(
        description="算子名称，如 resolve_geometry、calculate_ndvi、detect_change。"
    )


class GraphRAGArgs(BaseModel):
    query: str = Field(description="用户问题或检索用语。")
    top_k: int = Field(default=5, ge=1, le=20, description="向量召回数量占位。")


def build_neo4j_tools(client: Neo4jClient | None) -> list[StructuredTool]:
    if client is None:
        return []

    def _resolve_region(query_text: str, limit: int = 10) -> dict[str, Any]:
        rows = client.resolve_region(query_text, limit=limit)
        ids = [r.get("region_id") for r in rows if r.get("region_id")]
        return {
            "regions": rows,
            "linked_entities": ids,
            "count": len(rows),
        }

    def _operator_deps(operator_name: str) -> dict[str, Any]:
        return client.operator_dependencies(operator_name)

    return [
        StructuredTool.from_function(
            name="neo4j_resolve_region",
            description=(
                "从知识图谱解析行政区节点（Region）。规划 GIS 任务前优先调用，"
                "以获取规范 region_id 与层级。"
            ),
            args_schema=ResolveRegionArgs,
            func=lambda query_text, limit=10: _resolve_region(query_text, limit),
        ),
        StructuredTool.from_function(
            name="neo4j_operator_dependencies",
            description=(
                "查询某 GIS/分析算子（Operator）的 REQUIRES 依赖与关联数据集；"
                "用于确定工具调用顺序。"
            ),
            args_schema=OperatorDepsArgs,
            func=lambda operator_name: _operator_deps(operator_name),
        ),
    ]


def build_graphrag_tools(
    settings: Settings,
    *,
    neo4j_client: Neo4jClient | None = None,
) -> list[StructuredTool]:
    """形态 C：GRAPH_RAG_ENABLED=true 且具备 Neo4j+API 时走向量检索，否则返回占位说明。"""

    def _kg_graphrag_retrieve(query: str, top_k: int = 5) -> dict[str, Any]:
        return graphrag_retrieve(
            query,
            top_k=top_k,
            settings=settings,
            client=neo4j_client,
        )

    return [
        StructuredTool.from_function(
            name="kg_graphrag_retrieve",
            description=(
                "混合 Chunk 向量检索与知识图谱子图扩展（需 GRAPH_RAG_ENABLED=true 且已导入 Chunk 索引）。"
                "未配置时返回占位；精确查询可配合 neo4j_resolve_region / neo4j_operator_dependencies。"
            ),
            args_schema=GraphRAGArgs,
            func=lambda query, top_k=5: _kg_graphrag_retrieve(query, top_k),
        ),
    ]


# 向后兼容旧名称
build_graphrag_placeholder_tools = build_graphrag_tools
