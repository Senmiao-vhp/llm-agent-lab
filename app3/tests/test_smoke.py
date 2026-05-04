"""Smoke tests — no network calls required when OPENAI_API_KEY is absent."""

from __future__ import annotations

import os
import unittest


class TestGraphSmoke(unittest.TestCase):
    def test_invoke_without_api_key_ends_with_fatal(self) -> None:
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            from app3.config import Settings
            from app3.runtime.session import GraphSession

            session = GraphSession(Settings.from_env())
            out = session.invoke("hello")
            self.assertIn("fatal_error", out)
            self.assertIsNotNone(out.get("fatal_error"))
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old

    def test_graph_compiles_with_null_llm(self) -> None:
        from app3.config import Settings
        from app3.graph.builder import build_compiled_graph
        from app3.graph.context import GraphContext
        from app3.skills.registry import build_default_skill_tools

        ctx = GraphContext(
            settings=Settings(openai_api_key=None, openai_base_url=None, default_chat_model="gpt-4o-mini"),
            tools=tuple(build_default_skill_tools()),
            llm=None,
        )
        g = build_compiled_graph(ctx)
        self.assertIsNotNone(g)


if __name__ == "__main__":
    unittest.main()
