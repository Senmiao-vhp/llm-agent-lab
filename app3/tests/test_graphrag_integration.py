"""GraphRAG 集成检测：仅在配置齐全时跑真实 Neo4j + API（否则跳过）。"""

from __future__ import annotations

import os
import unittest
from dataclasses import replace

from app3.config import Settings
from app3.kg.graphrag import graphrag_retrieve
from app3.kg.neo4j_client import build_neo4j_client_from_settings


def _integration_ready() -> bool:
    return bool(os.getenv("NEO4J_URI", "").strip() and os.getenv("OPENAI_API_KEY", "").strip())


@unittest.skipUnless(_integration_ready(), "需要环境变量 NEO4J_URI 与 OPENAI_API_KEY")
class TestGraphRAGIntegration(unittest.TestCase):
    def test_live_graphrag_returns_ok_or_warn_empty(self) -> None:
        settings = Settings.from_env()
        client = build_neo4j_client_from_settings(settings)
        if client is None:
            self.skipTest("NEO4J_URI 不可用")
        try:
            if client.count_chunks_total() == 0:
                self.skipTest("数据库无 Chunk，请先导入 seed.cypher")
            if client.count_chunks_with_embedding() == 0:
                self.skipTest("Chunk 无 embedding，请先运行 embed_chunks")
            if not client.has_vector_index_named(settings.neo4j_chunk_vector_index):
                self.skipTest("缺少向量索引，请执行 vector_index.cypher")

            eff = replace(settings, graph_rag_enabled=True)
            out = graphrag_retrieve(
                "测试查询 NDVI",
                top_k=2,
                settings=eff,
                client=client,
            )
            self.assertIn(out.get("status"), ("ok", "error"))
            self.assertIn("kg_evidence", out)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
