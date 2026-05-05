"""OSM Nominatim 正向地理编码（std urllib；遵守 OSMF 使用率政策）。"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


def _env_gis_enabled() -> bool:
    v = (os.getenv("APP3_GIS_NOMINATIM") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _user_agent() -> str:
    return (os.getenv("APP3_NOMINATIM_USER_AGENT") or "").strip() or (
        "app3-agent-lab/0.1 (GIS lab; https://operations.osmfoundation.org/policies/nominatim/)"
    )


def admin_search_candidates(region: str) -> list[str]:
    """与 app2 类似的行政区短名补充，提高 Nominatim 命中率。"""
    s = (region or "").strip()
    out: list[str] = []
    if s:
        out.append(s)
    m = re.match(r"^(.+?市)([\u4e00-\u9fff]+(?:区|县|旗|盟|州|自治[州县]))$", s)
    if m:
        t = m.group(2)
        if t and t not in out:
            out.append(t)
    m2 = re.search(r"([\u4e00-\u9fff]{1,6}(?:区|县|旗|盟|州))$", s)
    if m2:
        t = m2.group(1)
        if t and t not in out:
            out.append(t)
    return list(dict.fromkeys(out))


def bbox_from_geojson(geojson: dict[str, Any]) -> list[float]:
    """返回 [min_lon, min_lat, max_lon, max_lat]，与 app2 GeometryOutput.bbox 一致。"""
    coords = geojson.get("coordinates")
    if not coords:
        raise ValueError("Invalid geometry geojson (missing coordinates).")

    xs: list[float] = []
    ys: list[float] = []

    def _walk(c: Any) -> None:
        if isinstance(c, (list, tuple)):
            if len(c) == 2 and all(isinstance(v, (int, float)) for v in c):
                xs.append(float(c[0]))
                ys.append(float(c[1]))
            else:
                for i in c:
                    _walk(i)

    _walk(coords)
    if not xs or not ys:
        raise ValueError("Unable to compute bbox from coordinates.")
    return [min(xs), min(ys), max(xs), max(ys)]


def _pick_polygon_geojson(feature: dict[str, Any]) -> dict[str, Any] | None:
    geo = feature.get("geojson")
    if not isinstance(geo, dict):
        return None
    t = geo.get("type")
    if t in ("Polygon", "MultiPolygon") and geo.get("coordinates") is not None:
        return geo
    if t == "GeometryCollection" and isinstance(geo.get("geometries"), list):
        for g in geo["geometries"]:
            if isinstance(g, dict) and g.get("type") in ("Polygon", "MultiPolygon") and g.get("coordinates") is not None:
                return g
    return None


def nominatim_resolve_region(region: str, *, timeout_s: float = 35.0) -> dict[str, Any]:
    """
    返回与 app2 `GeometryOutput` 对齐的字典：type, region, bbox, geometry_geojson, metadata。
    """
    if not _env_gis_enabled():
        raise RuntimeError(
            "Nominatim 已禁用（APP3_GIS_NOMINATIM=0）。解析行政区几何需要启用网络地理编码。"
        )

    region = (region or "").strip()
    if not region:
        raise ValueError("region 不能为空。")

    last_err: Exception | None = None
    candidates = admin_search_candidates(region)

    for i, q in enumerate(candidates):
        if i:
            time.sleep(1.1)
        query = f"{q}, 中国" if "中国" not in q and "香港" not in q and "澳门" not in q else q
        params = urllib.parse.urlencode(
            {
                "q": query,
                "format": "json",
                "limit": "1",
                "polygon_geojson": "1",
            }
        )
        url = f"{_SEARCH_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})

        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last_err = RuntimeError(f"HTTP {e.code} for query={query!r}: {e.reason}")
            continue
        except OSError as e:
            last_err = RuntimeError(f"network error for query={query!r}: {e}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            last_err = RuntimeError(f"invalid JSON from Nominatim: {e}")
            continue

        if not isinstance(data, list) or not data:
            last_err = RuntimeError(f"empty result for query={query!r}")
            continue

        gj = _pick_polygon_geojson(data[0])
        if gj is None:
            last_err = RuntimeError(f"no polygon geojson for query={query!r}")
            continue

        bbox = bbox_from_geojson(gj)
        return {
            "type": "geometry",
            "region": region,
            "bbox": bbox,
            "geometry_geojson": gj,
            "metadata": {
                "source": "OSM Nominatim (forward geocoding)",
                "matched_query": q,
                "display_name": data[0].get("display_name"),
                "osm_id": data[0].get("osm_id"),
                "lat": data[0].get("lat"),
                "lon": data[0].get("lon"),
            },
        }

    raise RuntimeError(
        f"Nominatim 无法解析行政区 {region!r}. Last: {last_err!r}"
    )
