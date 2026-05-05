"""delay 节点对 sleep 的调用。"""

from __future__ import annotations

import unittest
from unittest import mock

from app3.config import Settings
from app3.graph.context import GraphContext
from app3.nodes.delay import delay_node
from app3.skills.registry import build_default_skill_tools
from app3.state.agent_state import AgentState


class TestDelayNode(unittest.TestCase):
    def test_sleeps_and_clears(self) -> None:
        settings = Settings(
            openai_api_key=None,
            openai_base_url=None,
            default_chat_model="x",
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
        st: AgentState = {"pending_sleep_seconds": 0.5}
        with mock.patch("app3.nodes.delay.time.sleep", autospec=True) as sl:
            out = delay_node(st, ctx=ctx)
            sl.assert_called_once_with(0.5)
        self.assertEqual(out.get("pending_sleep_seconds"), 0.0)
        self.assertEqual(out.get("phase"), "delay")


if __name__ == "__main__":
    unittest.main()
