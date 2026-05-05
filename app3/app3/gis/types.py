from __future__ import annotations

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class OperatorOutput(BaseModel):
    """算子输出的统一外层：可增加字段，但必须保留稳定的 `type`。"""

    model_config = ConfigDict(extra="allow")

    type: str = Field(..., min_length=1)


class AreaStatsOutput(OperatorOutput):
    type: Literal["area_stats"] = "area_stats"
    area_sqm: float
    area_hectares: float
    area_mu: float
    unit: Literal["亩"] = "亩"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeometryOutput(OperatorOutput):
    type: Literal["geometry"] = "geometry"
    region: str
    bbox: list[float]
    geometry_geojson: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RasterSearchOutput(OperatorOutput):
    type: Literal["raster_search"] = "raster_search"
    source: str
    acquired: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

