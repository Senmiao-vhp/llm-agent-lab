from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)

_GEE_INIT_LOCK = threading.Lock()
_GEE_INITIALIZED_PROJECT: Optional[str] = None


@dataclass(frozen=True)
class GeeConfig:
    project_id: str


class GeeClient:
    """Earth Engine Python API 的薄封装：初始化与常用几何/影像辅助。"""

    def __init__(self, cfg: GeeConfig):
        if not cfg.project_id:
            raise ValueError("GEE project_id is required.")
        self.cfg = cfg
        try:
            import ee  # type: ignore

            self.ee = ee
            # ee.Initialize 是进程级全局状态；并发重复初始化可能造成连接重置/不稳定。
            # 同一 project_id 仅初始化一次；不同 project_id 时允许重新初始化，但仍加锁串行。
            global _GEE_INITIALIZED_PROJECT  # noqa: PLW0603
            with _GEE_INIT_LOCK:
                already = False
                try:
                    already = bool(getattr(self.ee.data, "_initialized", False))
                except Exception:
                    already = False
                if already and _GEE_INITIALIZED_PROJECT == cfg.project_id:
                    return
                self.ee.Initialize(project=cfg.project_id)
                _GEE_INITIALIZED_PROJECT = cfg.project_id
                logger.info("GEE initialized (project=%s).", cfg.project_id)
        except Exception as e:
            raise RuntimeError(
                f"Earth Engine init failed. Check auth/network/project_id. Original error: {e}"
            ) from e

    def geometry_from_geojson(self, geojson: Dict[str, Any]) -> Any:
        return self.ee.Geometry(geojson, None, False)

    def worldcover_image_for_year(self, year: int):
        """
        取 ESA WorldCover v200（10m 全球地表覆盖）。
        部分 GEE 环境集合内无 MAP_YEAR，仅首景可用；返回的 year_used：year≥2021 时为 2021，否则 2020（语义标注）。
        """
        year_used = 2021 if year >= 2021 else 2020
        col = self.ee.ImageCollection("ESA/WorldCover/v200")
        img = col.first()
        if img is None:
            raise RuntimeError("ESA WorldCover image not available in this GEE environment.")
        return img, year_used

