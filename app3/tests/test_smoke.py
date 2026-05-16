"""Smoke tests — no network calls required when OPENAI_API_KEY is absent."""

from __future__ import annotations

import unittest


class TestGraphSmoke(unittest.TestCase):
    def test_invoke_without_api_key_ends_with_fatal(self) -> None:
        from app3.config import settings_for_tests
        from app3.runtime.session import GraphSession

        session = GraphSession(
            settings_for_tests(openai_api_key=None, embedding_api_key=None, embedding_base_url=None)
        )
        try:
            out = session.invoke("hello")
            self.assertIn("fatal_error", out)
            self.assertIsNotNone(out.get("fatal_error"))
            self.assertEqual(out.get("fatal_subtype"), "fatal_config")
        finally:
            session.close()

    def test_graph_compiles_with_null_llm(self) -> None:
        from app3.config import settings_for_tests
        from app3.graph.builder import build_compiled_graph
        from app3.graph.context import GraphContext
        from app3.skills.registry import build_default_skill_tools

        settings = settings_for_tests(
            openai_api_key=None,
            openai_base_url=None,
            default_chat_model="gpt-4o-mini",
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
            neo4j_database=None,
        )
        ctx = GraphContext(
            settings=settings,
            tools=tuple(build_default_skill_tools(settings)),
            llm=None,
        )
        g = build_compiled_graph(ctx)
        self.assertIsNotNone(g)


if __name__ == "__main__":
    unittest.main()
