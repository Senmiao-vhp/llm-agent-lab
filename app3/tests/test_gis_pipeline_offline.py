"""GIS pipeline 工具离线行为（不初始化 GEE）。"""

from __future__ import annotations

import unittest

from app3.config import Settings
from app3.gis.pipeline_tool import execute_pipeline_json


class TestPipelineOffline(unittest.TestCase):
    def test_pipeline_requires_gee_project(self) -> None:
        s = Settings(
            openai_api_key=None,
            openai_base_url=None,
            default_chat_model="x",
            neo4j_uri=None,
            neo4j_user=None,
            neo4j_password=None,
            neo4j_database=None,
            gee_project_id=None,
        )
        out = execute_pipeline_json('{"tasks":[]}', s)
        self.assertFalse(out.get("success"))
        self.assertIn("GEE", str(out.get("message") or ""))


if __name__ == "__main__":
    unittest.main()
