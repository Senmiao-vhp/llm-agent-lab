"""Smoke tests — no network calls required when OPENAI_API_KEY is absent."""

from __future__ import annotations

import os
import unittest


class TestGraphSmoke(unittest.TestCase):
    def test_invoke_without_api_key_ends_with_fatal(self) -> None:
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        old_emb = os.environ.pop("EMBEDDING_API_KEY", None)
        old_skip = os.environ.get("APP3_SKIP_ENV_FILE")
        os.environ["APP3_SKIP_ENV_FILE"] = "1"
        try:
            from app3.config import Settings
            from app3.runtime.session import GraphSession

            session = GraphSession(Settings.from_env())
            out = session.invoke("hello")
            self.assertIn("fatal_error", out)
            self.assertIsNotNone(out.get("fatal_error"))
            self.assertEqual(out.get("fatal_subtype"), "fatal_config")
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key
            if old_emb is not None:
                os.environ["EMBEDDING_API_KEY"] = old_emb
            if old_skip is None:
                os.environ.pop("APP3_SKIP_ENV_FILE", None)
            else:
                os.environ["APP3_SKIP_ENV_FILE"] = old_skip

    def test_graph_compiles_with_null_llm(self) -> None:
        from app3.config import Settings
        from app3.graph.builder import build_compiled_graph
        from app3.graph.context import GraphContext
        from app3.skills.registry import build_default_skill_tools

        settings = Settings(
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
