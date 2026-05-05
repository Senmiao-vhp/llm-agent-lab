"""知识图谱：注册表与形态 C 占位。"""

from __future__ import annotations

import unittest

from app3.config import Settings
from app3.kg.graphrag import graphrag_retrieve_placeholder
from app3.skills.registry import build_default_skill_tools


def _base_settings() -> Settings:
    return Settings(
        openai_api_key=None,
        openai_base_url=None,
        default_chat_model="x",
        neo4j_uri=None,
        neo4j_user=None,
        neo4j_password=None,
        neo4j_database=None,
    )


class TestKGRegistry(unittest.TestCase):
    def test_tools_include_gis_and_graphrag_without_neo4j(self) -> None:
        tools = list(build_default_skill_tools(_base_settings()))
        names = {t.name for t in tools}
        self.assertIn("resolve_geometry", names)
        self.assertIn("kg_graphrag_retrieve", names)
        self.assertNotIn("neo4j_resolve_region", names)

    def test_graphrag_placeholder_shape(self) -> None:
        out = graphrag_retrieve_placeholder("test query", top_k=3)
        self.assertEqual(out["status"], "placeholder")
        self.assertIn("kg_evidence", out)


if __name__ == "__main__":
    unittest.main()
