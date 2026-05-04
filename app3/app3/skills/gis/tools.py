"""GIS 占位符工具。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ResolveGeometryArgs(BaseModel):
    region: str = Field(description="可读的区域名称，例如城市或县。")


def _resolve_geometry_stub(region: str) -> dict[str, Any]:
    # TODO: 实现解析器（GEE、本地行政区域层、 HTTP 微服务、 …）
    return {"type": "geometry_stub", "region": region, "note": "TODO 实现"}


def build_gis_placeholder_tools() -> Sequence[StructuredTool]:
    return [
        StructuredTool.from_function(
            name="resolve_geometry",
            description="将区域名称解析为几何元数据（占位符）。",
            args_schema=ResolveGeometryArgs,
            func=_resolve_geometry_stub,
        )
    ]
