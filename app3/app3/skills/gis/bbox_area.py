"""由经纬度 bbox 估算地表面积（扁球近似，用于演示；非精确法制测量）。"""

from __future__ import annotations

import math
from typing import Any


def approximate_bbox_area_sqm(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    """
    使用球面近似：在中纬取 cos(lat) 修正经向长度。
    west/south/east/north 为度；跨越反子午线时需调用方先规范化 bbox。
    """
    if east <= west or north <= south:
        raise ValueError("bbox 要求 west < east 且 south < north（单位：度）。")

    R = 6371000.0
    lat_mid = math.radians((south + north) / 2.0)
    dlat = math.radians(north - south)
    dlon = math.radians(east - west)
    height_m = R * dlat
    width_m = R * dlon * max(math.cos(lat_mid), 1e-6)
    area_sqm = abs(width_m * height_m)
    sqm_per_mu = 666.666667
    area_mu = area_sqm / sqm_per_mu
    area_hectares = area_sqm / 10000.0
    return {
        "area_sqm": round(area_sqm, 2),
        "area_hectares": round(area_hectares, 4),
        "area_mu": round(area_mu, 4),
        "unit_primary": "亩",
        "metadata": {
            "method": "sphere_cos_latitude_bbox",
            "disclaimer": "扁球近似，仅作粗估；不可直接作为法定面积依据。",
        },
    }
