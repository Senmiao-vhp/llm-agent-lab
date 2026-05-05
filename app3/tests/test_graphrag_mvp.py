"""GraphRAG MVP：占位 / mock 检索逻辑（无需实时 Neo4j）。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app3.config import Settings
from app3.kg.graphrag import graphrag_retrieve, graphrag_retrieve_placeholder


def _settings_base(**kwargs: object) -> Settings:
    base = dict(
        openai_api_key=None,
        openai_base_url=None,
        default_chat_model="x",
        neo4j_uri=None,
        neo4j_user=None,
        neo4j_password=None,
        neo4j_database=None,
        graph_rag_enabled=False,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        neo4j_chunk_vector_index="chunk_embedding_index",
    )
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


class TestGraphRAGMVP(unittest.TestCase):
    def test_placeholder_when_disabled(self) -> None:
        out = graphrag_retrieve(
            "耕地监测怎么做",
            top_k=3,
            settings=_settings_base(graph_rag_enabled=False),
            client=None,
        )
        self.assertEqual(out["status"], "placeholder")

    def test_placeholder_shape_module(self) -> None:
        out = graphrag_retrieve_placeholder("x")
        self.assertEqual(out["status"], "placeholder")
        self.assertIn("kg_evidence", out)

    def test_ok_path_with_mock_client(self) -> None:
        client = MagicMock()
        client.vector_query_chunks.return_value = [
            {"chunk_id": "chunk_op_resolve_geometry", "text": "边界解析", "score": 0.9},
        ]
        client.graphrag_expand_subgraph.return_value = [
            {
                "chunk_id": "chunk_op_resolve_geometry",
                "chunk_text": "边界解析",
                "anchor_label": "Operator",
                "anchor_id": "resolve_geometry",
                "rel_type": None,
                "target_label": None,
                "target_id": None,
            },
        ]
        with unittest.mock.patch("app3.kg.graphrag.embed_query_text", return_value=[0.1] * 1536):
            out = graphrag_retrieve(
                "如何解析几何",
                top_k=2,
                settings=_settings_base(
                    openai_api_key="sk-test",
                    graph_rag_enabled=True,
                ),
                client=client,
            )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(len(out["kg_evidence"]), 1)
        ev0 = out["kg_evidence"][0]
        self.assertEqual(ev0["chunk_id"], "chunk_op_resolve_geometry")
        self.assertIn("subgraph_edges", ev0)


if __name__ == "__main__":
    unittest.main()
