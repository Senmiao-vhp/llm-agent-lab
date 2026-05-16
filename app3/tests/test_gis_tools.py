"""GIS 工具：Nominatim 解析与 bbox 面积粗算。"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app3.config import settings_for_tests
from app3.skills.gis.bbox_area import approximate_bbox_area_sqm
from app3.skills.gis.nominatim import bbox_from_geojson, nominatim_resolve_region


class TestBboxArea(unittest.TestCase):
    def test_approximate_bbox_positive(self) -> None:
        out = approximate_bbox_area_sqm(116.0, 39.7, 117.0, 40.2)
        self.assertGreater(out["area_sqm"], 0)
        self.assertEqual(out["unit_primary"], "亩")


class TestNominatimMock(unittest.TestCase):
    def test_resolve_returns_geometry_type(self) -> None:
        fake = json.dumps(
            [
                {
                    "lat": "39.9",
                    "lon": "116.4",
                    "display_name": "北京市",
                    "osm_id": 123,
                    "geojson": {
                        "type": "Polygon",
                        "coordinates": [[[116.0, 39.7], [117.0, 39.7], [117.0, 40.5], [116.0, 40.5], [116.0, 39.7]]],
                    },
                }
            ]
        ).encode("utf-8")

        class _Resp:
            def __enter__(self) -> "_Resp":
                return self

            def __exit__(self, *a: object) -> None:
                return None

            def read(self) -> bytes:
                return fake

        st = settings_for_tests(gis_nominatim_enabled=True)
        with patch("urllib.request.urlopen", return_value=_Resp()):
            out = nominatim_resolve_region("北京市", settings=st)
        self.assertEqual(out["type"], "geometry")
        self.assertEqual(out["region"], "北京市")
        self.assertEqual(len(out["bbox"]), 4)
        self.assertEqual(out["geometry_geojson"]["type"], "Polygon")


class TestBboxFromGeojson(unittest.TestCase):
    def test_polygon(self) -> None:
        gj = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]]}
        self.assertEqual(bbox_from_geojson(gj), [0.0, 0.0, 2.0, 1.0])


if __name__ == "__main__":
    unittest.main()
