"""检测可选 GIS 重依赖是否可用（未安装 `[gis]` extras 时为 False）。"""

from __future__ import annotations


def gis_stack_importable() -> bool:
    try:
        import ee  # noqa: F401
        import rasterio  # noqa: F401
        return True
    except ImportError:
        return False
