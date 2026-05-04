"""中心工具注册表，用于将工具传递给 GraphContext。"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from app3.skills.gis.tools import build_gis_placeholder_tools


def build_default_skill_tools() -> Sequence[BaseTool]:
    return [*build_gis_placeholder_tools()]
