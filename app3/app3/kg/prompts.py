"""规划节点使用的系统提示片段 — 强调形态 A 先查 Neo4j。"""

# 在实现 plan_node 的 LLM 调用时，将此段并入 system prompt。
PLAN_KG_FIRST_SUPPLEMENT = """
领域规则（知识图谱 Neo4j）：
- 在编排任何 GIS 算子（如 resolve_geometry、NDVI、变化检测）之前，应优先调用工具
  neo4j_resolve_region（若用户提到地名或行政区）与 neo4j_operator_dependencies（若需确认算子依赖顺序）。
- 形态 C 检索可试用 kg_graphrag_retrieve；若返回 placeholder，则依赖上述精确查询工具。
"""
