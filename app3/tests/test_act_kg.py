"""act_node：工具执行与 kg_* 状态合并。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app3.config import Settings
from app3.graph.context import GraphContext
from app3.nodes.act import act_node
from app3.skills.registry import build_default_skill_tools
from app3.state.agent_state import AgentState, ErrorClass


class TestActKgMerge(unittest.TestCase):
    def test_neo4j_tool_updates_linked_entities(self) -> None:
        settings = Settings(
            openai_api_key=None,
            openai_base_url=None,
            default_chat_model="x",
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
            neo4j_database=None,
        )
        mock_tool = MagicMock()
        mock_tool.name = "neo4j_resolve_region"
        mock_tool.invoke = MagicMock(
            return_value={
                "regions": [{"region_id": "CN-110000", "name": "北京市"}],
                "linked_entities": ["CN-110000"],
                "count": 1,
            }
        )
        ctx = GraphContext(settings=settings, tools=(mock_tool,), llm=None)
        st: AgentState = {
            "plan_result": {
                "tool_calls": [
                    {
                        "name": "neo4j_resolve_region",
                        "args": {"query_text": "北京", "limit": 5},
                        "id": "call-1",
                    }
                ],
            },
            "linked_entities": [],
            "kg_context": None,
        }
        out = act_node(st, ctx=ctx)
        self.assertEqual(out.get("error_class"), ErrorClass.NONE)
        self.assertEqual(out.get("linked_entities"), ["CN-110000"])
        self.assertIsNotNone(out.get("kg_context"))
        ctx_kg = out.get("kg_context")
        assert isinstance(ctx_kg, dict)
        self.assertIn("neo4j_resolve_region", ctx_kg)

    def test_unknown_tool_is_recoverable(self) -> None:
        settings = Settings(
            openai_api_key=None,
            openai_base_url=None,
            default_chat_model="x",
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
            neo4j_database=None,
        )
        tools = tuple(build_default_skill_tools(settings))
        ctx = GraphContext(settings=settings, tools=tools, llm=None)
        st: AgentState = {
            "plan_result": {
                "tool_calls": [
                    {"name": "nonexistent_tool_xyz", "args": {}, "id": "x"},
                ],
            },
        }
        out = act_node(st, ctx=ctx)
        self.assertEqual(out.get("error_class"), ErrorClass.RECOVERABLE)
        self.assertIn("unknown tool", (out.get("last_tool_error") or "").lower())


if __name__ == "__main__":
    unittest.main()
