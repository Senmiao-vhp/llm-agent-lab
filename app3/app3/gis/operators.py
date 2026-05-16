from __future__ import annotations

import logging
import os
import re
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.warp import reproject, Resampling
from rasterio.warp import transform as warp_transform

from app3.gis.gee_client import GeeClient
from app3.gis.types import AreaStatsOutput, GeometryOutput

from app3.gis.unpacker import GlobeLandUnpacker
from app3.gis.processor import CLASS_MAPPING, GlobeLandProcessor, GisProcessor
from app3.gis.change_detector import ChangeDetector
from app3.gis.downloader import GEEDownloader
from app3.gis.gaul_names import gaul_name_candidates, strip_cn_admin_suffix
from app3.gis.executor_models import ExecutorConfig


logger = logging.getLogger(__name__)


class GisOperators:
    """Executor 调用的 GIS 算子；各方法返回含稳定 `type` 字段的字典。"""

    def __init__(self, gee: GeeClient, cfg: ExecutorConfig):
        self.gee = gee
        self._cfg = cfg
        self._gee_downloader: Optional[GEEDownloader] = None
        self._gee_downloader_lock = threading.Lock()
        self._unpacker = GlobeLandUnpacker(cfg.globeland30_dir, cfg.processed_data_dir)
        # 延迟初始化：本地 geoBoundaries（中国），GAUL 未命中区县名时使用
        self._local_admin: Optional[Any] = None
        self._local_admin_lock = threading.Lock()

    def resolve_geometry(self, params: Dict[str, Any], _inputs: Any) -> Dict[str, Any]:
        region = str(params.get("region") or "").strip()
        if not region:
            raise ValueError("resolve_geometry requires `region`.")
        e_gee: Optional[Exception] = None
        e_local: Optional[Exception] = None
        e_nom: Optional[Exception] = None
        try:
            hit = self._resolve_geometry_via_gee(region)
        except Exception as e:
            e_gee = e
            logger.info("GEE/GAUL failed for region=%s: %s; trying local geoBoundaries.", region, e)
            try:
                hit = self._resolve_geometry_via_local_geoboundaries(region)
            except Exception as e2:
                e_local = e2
                if self._cfg.geo_fallback_nominatim:
                    logger.info("local geoBoundaries failed; trying Nominatim (APP3_GEO_FALLBACK_NOMINATIM=true).")
                    try:
                        hit = self._resolve_geometry_via_nominatim(region)
                    except Exception as e3:
                        e_nom = e3
                        raise RuntimeError(
                            f"Failed to resolve geometry for region={region!r}.\n"
                            f"- GEE/GAUL: {e_gee!s}\n"
                            f"- local geoBoundaries: {e_local!s}\n"
                            f"- Nominatim: {e_nom!s}"
                        ) from e3
                else:
                    raise RuntimeError(
                        f"Failed to resolve geometry for region={region!r}.\n"
                        f"- GEE/GAUL: {e_gee!s}\n"
                        f"- local geoBoundaries: {e_local!s}\n"
                        "To try OSM Nominatim, set geo_fallback_nominatim in Settings / APP3_GEO_FALLBACK_NOMINATIM=true (requires nominatim.openstreetmap.org access)."
                    ) from e2
        out = GeometryOutput(
            region=region,
            bbox=hit["bbox"],
            geometry_geojson=hit["geometry_geojson"],
            metadata=hit["metadata"],
        )
        return out.model_dump()

    @staticmethod
    def _admin_search_candidates(region: str) -> List[str]:
        """
        生成用于 GAUL/OSM 的行政区名称候选。区市连写（如 成都市金牛区）时补充「金牛区」等短名。
        """
        s = (region or "").strip()
        out: List[str] = []
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

    def _resolve_geometry_via_local_geoboundaries(self, region: str) -> Dict[str, Any]:
        """通过 AdminBoundaryManager 使用打包的 geoBoundaries（中国）；数据已在 data/raw/admin_boundaries 时可离线。"""
        try:
            from shapely.geometry import mapping
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("geopandas/shapely required for local admin boundaries.") from e
        from app3.gis.downloader import AdminBoundaryManager

        if self._local_admin is None:
            with self._local_admin_lock:
                if self._local_admin is None:
                    self._local_admin = AdminBoundaryManager(
                        "CHN",
                        raw_admin_boundary_dir=self._cfg.raw_admin_boundary_dir,
                        processed_admin_boundary_dir=self._cfg.processed_admin_boundary_dir,
                    )
        last: Optional[Exception] = None
        for q in self._admin_search_candidates(region):
            try:
                hit = self._local_admin.find_geometry(q, prefer_level="ADM3")
            except Exception as e:
                last = e
                continue
            geom = hit.get("geometry")
            if geom is None:
                continue
            gj = mapping(geom)
            bbox = list(geom.bounds)
            return {
                "geometry_geojson": gj,
                "bbox": bbox,
                "metadata": {
                    "source": f"local geoBoundaries ({hit.get('level', '')})",
                    "matched_name": str(hit.get("name", q)),
                },
            }
        err = f"no CHN admin match in geoBoundaries for {region!r}"
        if last is not None:
            err = f"{err}. Last: {last!s}"
        raise RuntimeError(err)

    def _resolve_geometry_via_nominatim(self, region: str) -> Dict[str, Any]:
        """备选：OSM Nominatim 正向地理编码（遵守使用率政策，约 1 次/秒）。"""
        try:
            import requests
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("requests is required for Nominatim fallback.") from e
        # https://operations.osmfoundation.org/policies/nominatim/
        last_err: Optional[Exception] = None
        for i, q in enumerate(self._admin_search_candidates(region)):
            if i:
                time.sleep(1.1)
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{q}, 中国" if "中国" not in q and "香港" not in q else q, "format": "json", "limit": 1, "polygon_geojson": 1},
                headers={"User-Agent": "app3-agent-lab/1.0 (GIS; local use; nominatim fallback)"},
                timeout=35,
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                last_err = RuntimeError(f"empty result for query={q!r}")
                continue
            geo = data[0].get("geojson")
            if not isinstance(geo, dict):
                last_err = RuntimeError(f"no geojson for query={q!r}")
                continue
            gj: Optional[Dict[str, Any]] = None
            t = geo.get("type")
            if t in ("Polygon", "MultiPolygon") and geo.get("coordinates") is not None:
                gj = geo
            elif t == "GeometryCollection" and isinstance(geo.get("geometries"), list):
                for g in geo["geometries"]:
                    if not isinstance(g, dict):
                        continue
                    if g.get("type") in ("Polygon", "MultiPolygon") and g.get("coordinates") is not None:
                        gj = g
                        break
            if gj is None:
                last_err = RuntimeError(f"no polygon in geojson for query={q!r}")
                continue
            bbox = self._bbox_from_geojson(gj)
            return {
                "geometry_geojson": gj,
                "bbox": bbox,
                "metadata": {
                    "source": "OSM Nominatim (forward geocoding)",
                    "matched_query": q,
                    "osm_id": data[0].get("osm_id"),
                },
            }
        raise RuntimeError(f"Nominatim: no boundary for {region!r}. Last error: {last_err!r}")

    def _resolve_geometry_via_gee(self, region: str) -> Dict[str, Any]:
        """经 GEE FAO/GAUL 解析行政边界；GAUL 多为英文名，需对常见中文输入做映射。"""
        ee = self.gee.ee
        cn = strip_cn_admin_suffix(region)
        extra = []
        for x in GisOperators._admin_search_candidates(region) + [region]:
            if x and x not in extra:
                extra.append(x)
        merge_city_district = "市" in region and ("区" in region or "县" in region) and len(region) > 4
        # 市区连写时避免把“去后缀短名”塞进去（可能导致 GAUL 命中到不相关的同名 ADM2）
        if merge_city_district and cn:
            extra = [x for x in extra if x != cn]
        candidates = gaul_name_candidates(region, extra_candidates=extra)

        def _gaul_level_order(name: str) -> list[str]:
            """
            根据输入形态决定 GAUL level 的优先级，减少无谓查询并提升命中率。
            - 省/自治区/特别行政区：优先 ADM1
            - 市（含“市+区县连写”）：优先 ADM2
            - 其它：默认 ADM1→ADM2
            """
            s = (name or "").strip()
            if merge_city_district or s.endswith("市"):
                return ["ADM2", "ADM1"]
            if s.endswith(("省", "自治区", "特别行政区")):
                return ["ADM1", "ADM2"]
            return ["ADM1", "ADM2"]

        def _try_gaul_match(fc, field: str, source: str) -> Optional[Dict[str, Any]]:
            # 将多候选合并为 inList 过滤，减少 getInfo() 次数；候选太多时分批（避免潜在 inList 限制）。
            names = [n for n in candidates if isinstance(n, str) and n.strip()]
            if not names:
                return None
            chunk_size = 25
            for i in range(0, len(names), chunk_size):
                chunk = names[i : i + chunk_size]
                f = fc.filter(ee.Filter.inList(field, chunk)).limit(1).first()
                info = f.getInfo() if f else None
                if info and info.get("geometry"):
                    gj = info["geometry"]
                    bbox = self._bbox_from_geojson(gj)
                    matched = None
                    try:
                        matched = (info.get("properties") or {}).get(field)
                    except Exception:
                        matched = None
                    return {
                        "geometry_geojson": gj,
                        "bbox": bbox,
                        "metadata": {"source": source, "matched_name": matched},
                    }
            return None

        order = _gaul_level_order(region)
        for lv in order:
            if lv == "ADM1":
                fc1 = ee.FeatureCollection("FAO/GAUL/2015/level1")
                hit1 = _try_gaul_match(fc1, "ADM1_NAME", "GEE:FAO/GAUL/2015/level1")
                if hit1:
                    return hit1
            elif lv == "ADM2":
                fc2 = ee.FeatureCollection("FAO/GAUL/2015/level2")
                hit2 = _try_gaul_match(fc2, "ADM2_NAME", "GEE:FAO/GAUL/2015/level2")
                if hit2:
                    return hit2

        raise RuntimeError("No GAUL match found.")

    @staticmethod
    def _bbox_from_geojson(geojson: Dict[str, Any]) -> list[float]:
        coords = geojson.get("coordinates")
        if not coords:
            raise ValueError("Invalid geometry geojson (missing coordinates).")

        xs: list[float] = []
        ys: list[float] = []

        def _walk(c):
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

    def load_globeland30(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """载入 GlobeLand30(2020) 掩膜片段，按行政几何裁剪；可能跨多分幅。"""
        if not isinstance(inputs, dict) or inputs.get("type") != "geometry":
            raise ValueError("load_globeland30 requires GeometryOutput as input.")

        bbox = inputs["bbox"]
        boundary_geojson = inputs["geometry_geojson"]
        target_object = str(params.get("target_object") or "耕地")
        region = str(params.get("region") or inputs.get("region") or "")
        export_geojson = bool(params.get("export_geojson", False))
        max_features = int(params.get("max_features", 5000))
        min_feature_area_pixels = int(params.get("min_feature_area_pixels", 0) or 0)

        tile_names = self._unpacker.get_tile_names_from_bbox(bbox)
        pieces = []
        missing = []
        for tile in tile_names:
            tif_path = self._unpacker.unpack_tile(tile)
            if not tif_path:
                missing.append(tile)
                continue
            proc = GlobeLandProcessor(tif_path)
            mask, profile = proc.extract_mask(
                target_object=target_object,
                bbox=bbox,
                geometry=boundary_geojson,
            )
            if mask.size == 0:
                continue
            pieces.append({"tile": tile, "mask": mask.astype(np.uint8), "profile": profile})

        if not pieces:
            if missing:
                raise FileNotFoundError(f"Missing GlobeLand30 tiles locally: {missing}")
            raise RuntimeError(f"Failed to extract GlobeLand30 mask for region={region}")

        out: Dict[str, Any] = {
            "type": "mask_pieces",
            "region": region,
            "bbox": bbox,
            "boundary_geojson": boundary_geojson,
            "target_object": target_object,
            "pieces": pieces,
            "pixel_area_sqm": 900.0,  # GlobeLand30 约 30m 像元，面积约 900 m²
        }

        # 可选：将耕地掩膜矢量化为 GeoJSON 图斑并落盘，供前端地图加载（默认关闭，避免大 AOI 产生巨量要素）
        if export_geojson:
            try:
                from rasterio.features import shapes, sieve
                from rasterio.warp import transform_geom

                features: List[Dict[str, Any]] = []
                truncated = False
                for p in pieces:
                    mask_u8 = p.get("mask")
                    prof = p.get("profile") or {}
                    if mask_u8 is None or prof.get("transform") is None or prof.get("crs") is None:
                        continue
                    mask_u8 = np.asarray(mask_u8, dtype=np.uint8)
                    if min_feature_area_pixels and min_feature_area_pixels > 1:
                        try:
                            mask_u8 = sieve(mask_u8, size=int(min_feature_area_pixels))
                        except Exception:
                            pass
                    transform = Affine(*list(prof["transform"]))
                    src_crs = str(prof["crs"])
                    for geom, val in shapes(mask_u8, mask=mask_u8, transform=transform):
                        if int(val) != 1:
                            continue
                        geom_wgs84 = transform_geom(src_crs, "EPSG:4326", geom, precision=6)
                        features.append(
                            {
                                "type": "Feature",
                                "properties": {"tile": p.get("tile")},
                                "geometry": geom_wgs84,
                            }
                        )
                        if len(features) >= max_features:
                            truncated = True
                            break
                    if truncated:
                        break

                fc = {"type": "FeatureCollection", "features": features}
                output_dir = os.path.join(self._cfg.processed_data_dir, "geojson")
                os.makedirs(output_dir, exist_ok=True)
                filename = f"app3_baseline_{int(time.time())}.geojson"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(fc, f, ensure_ascii=False)
                out["geojson_path"] = filepath
                out["geojson_truncated"] = truncated
                out["geojson_meta"] = {
                    "max_features": max_features,
                    "min_feature_area_pixels": min_feature_area_pixels,
                }
            except Exception as e:  # noqa: BLE001
                logger.warning("baseline mask vectorization failed: %s", e)

        return out

    def search_satellite(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """经 GEE 获取 Sentinel-2 B4/B8，本地缓存 TIF，返回数组与元数据。"""
        if not isinstance(inputs, dict) or inputs.get("type") != "geometry":
            raise ValueError("search_satellite requires GeometryOutput as input.")

        if self._gee_downloader is None:
            with self._gee_downloader_lock:
                if self._gee_downloader is None:
                    self._gee_downloader = GEEDownloader(
                        self.gee.cfg.project_id,
                        processed_data_dir=self._cfg.processed_data_dir,
                        raw_admin_boundary_dir=self._cfg.raw_admin_boundary_dir,
                        processed_admin_boundary_dir=self._cfg.processed_admin_boundary_dir,
                    )

        region = str(params.get("region") or inputs.get("region") or "")
        year = int(params.get("year") or datetime.now().year)
        max_cloud = float(params.get("max_cloud_cover") or 20.0)
        bbox = inputs["bbox"]

        # 控制 GEE 导出体量：范围大时提高 scale_m，减轻 getDownloadURL 压力
        if "scale_m" in params:
            scale_m = int(params.get("scale_m") or 20)
        else:
            bbox_area_deg2 = max(0.0, (bbox[2] - bbox[0])) * max(0.0, (bbox[3] - bbox[1]))
            if bbox_area_deg2 > 0.5:
                scale_m = 300
            elif bbox_area_deg2 > 0.12:
                scale_m = 200
            else:
                scale_m = 60

        download_timeout = int(params.get("download_timeout", 300))

        # ±N 天绕 7-20 夏窗；趋势任务可放宽容差以通过个别难年(云/重试)
        half = int(params.get("date_half_width_days", 20))
        dt = datetime(year, 7, 20)
        start = (dt - timedelta(days=half)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=half)).strftime("%Y-%m-%d")

        try:
            red, nir, meta = self._gee_downloader.fetch_s2_b4_b8(
                bbox=bbox,
                geometry_geojson=inputs["geometry_geojson"],
                start_date=start,
                end_date=end,
                max_cloud_cover=max_cloud,
                scale=scale_m,
                download_timeout=download_timeout,
            )
        except Exception as e:  # noqa: BLE001
            try:
                from tenacity import RetryError
            except ImportError:  # pragma: no cover
                raise
            if isinstance(e, RetryError):
                c = e.last_attempt.exception() if e.last_attempt else e
                raise RuntimeError(
                    f"GEE S2 拉取在 tenacity 重试后仍失败 (year={year}): {c!s}"
                ) from c
            raise
        return {
            "type": "raster_data",
            "region": region,
            "red": red,
            "nir": nir,
            "metadata": meta,
        }

    def calculate_ndvi(self, _params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        if not isinstance(inputs, dict) or inputs.get("type") != "raster_data":
            raise ValueError("calculate_ndvi requires raster_data input.")
        ndvi = ChangeDetector.calculate_ndvi(inputs["red"], inputs["nir"])
        return {"type": "ndvi", "ndvi": ndvi}

    def detect_change(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """疑似流失：GlobeLand30 基线为耕地掩膜且 NDVI 低于阈值。"""
        if not isinstance(inputs, list) or len(inputs) < 3:
            raise ValueError("detect_change requires [mask_pieces, ndvi, raster_data] inputs.")
        base = inputs[0]
        ndvi_obj = inputs[1]
        raster = inputs[2]
        if not isinstance(base, dict) or base.get("type") != "mask_pieces":
            raise ValueError("detect_change first input must be mask_pieces.")
        if not isinstance(ndvi_obj, dict) or ndvi_obj.get("type") != "ndvi":
            raise ValueError("detect_change second input must be ndvi.")
        if not isinstance(raster, dict) or raster.get("type") != "raster_data":
            raise ValueError("detect_change third input must be raster_data.")

        thr = float(params.get("ndvi_threshold", 0.15))
        export_geojson = bool(params.get("export_geojson", False))
        max_features = int(params.get("max_features", 2000))
        min_feature_area_pixels = int(params.get("min_feature_area_pixels", 0) or 0)
        proc_res = GisProcessor.align_and_detect(
            ndvi=ndvi_obj["ndvi"],
            mask_pieces=base.get("pieces"),
            mask_data=None,
            raster_meta=raster.get("metadata") or {},
            ndvi_threshold=thr,
            boundary_geojson=base.get("boundary_geojson"),
            export_geojson=export_geojson,
            max_features=max_features,
            min_feature_area_pixels=min_feature_area_pixels,
        )
        out: Dict[str, Any] = {"type": "analysis_result", **proc_res, "ndvi_threshold": thr}

        # 大图斑落盘供前端加载，减小 JSON 体积
        if export_geojson and isinstance(out.get("change_geojson"), dict):
            output_dir = os.path.join(self._cfg.processed_data_dir, "geojson")
            os.makedirs(output_dir, exist_ok=True)
            filename = f"app3_change_{int(time.time())}.geojson"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(out["change_geojson"], f, ensure_ascii=False)
            out["change_geojson_path"] = filepath
            out["geojson_truncated"] = bool(out.get("geojson_truncated", False))

        return out

    def area_stats(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """按 mask_pieces（基线）或 analysis_result（变化掩膜）汇总像元并换算面积。"""
        label = params.get("label")
        data = inputs[0] if isinstance(inputs, list) and inputs else inputs

        pixel_area_sqm = 900.0
        total_pixels = 0

        if isinstance(data, dict) and data.get("type") == "mask_pieces":
            pixel_area_sqm = float(data.get("pixel_area_sqm", 900.0))
            for p in data.get("pieces", []):
                total_pixels += int(np.sum(p.get("mask", 0)))
        elif isinstance(data, dict) and data.get("type") == "analysis_result":
            pixel_area_sqm = float(data.get("pixel_area_sqm", 900.0))
            total_pixels = int(np.sum(data.get("mask", 0)))
        else:
            raise ValueError("area_stats expects mask_pieces or analysis_result input.")

        area_sqm = total_pixels * pixel_area_sqm
        area_hectares = area_sqm / 10000.0
        area_mu = area_sqm / 666.66666667
        meta: Dict[str, Any] = {"label": label, "total_pixels": total_pixels, "pixel_area_sqm": pixel_area_sqm}
        if isinstance(data, dict) and data.get("type") == "analysis_result":
            if data.get("change_geojson_path"):
                meta["change_geojson_path"] = data.get("change_geojson_path")
            if "geojson_truncated" in data:
                meta["geojson_truncated"] = data.get("geojson_truncated")
        return AreaStatsOutput(
            area_sqm=round(area_sqm, 2),
            area_hectares=round(area_hectares, 2),
            area_mu=round(area_mu, 2),
            metadata=meta,
        ).model_dump()

    def calculate_holdings(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        if not isinstance(inputs, list) or len(inputs) < 2:
            raise ValueError("calculate_holdings requires [baseline_stats, loss_stats].")
        baseline, loss = inputs[0], inputs[1]
        year = int(params.get("year") or datetime.now().year)
        b = float((baseline or {}).get("area_mu", 0.0))
        l_raw = float((loss or {}).get("area_mu", 0.0))

        # 注意：baseline_stats 通常来自 GL30 30m 掩膜（900m²/px），
        # loss_stats 来自对齐到 Sentinel 栅格后的变化掩膜（常见 60m=3600m²/px）。
        # 若直接用两者的“亩”相减会出现 l_raw > b 的假象（量纲不一致）。
        b_meta = (baseline.get("metadata") or {}) if isinstance(baseline, dict) else {}
        l_meta = (loss.get("metadata") or {}) if isinstance(loss, dict) else {}
        b_pa = float(b_meta.get("pixel_area_sqm", 0.0) or 0.0)
        l_pa = float(l_meta.get("pixel_area_sqm", 0.0) or 0.0)

        l_adj = l_raw
        adjust_note: str = ""
        if b_pa > 0 and l_pa > 0 and abs(b_pa - l_pa) > 1e-6:
            # 将 loss 以像元面积比例换算到 baseline 的“亩”量纲（近似校正，用于避免明显不合理的 0 保有量）。
            ratio = b_pa / l_pa
            l_adj = l_raw * ratio
            adjust_note = f"loss_area_mu 已按像元面积比校正：baseline_pixel_area_sqm={b_pa:g}, loss_pixel_area_sqm={l_pa:g}, ratio={ratio:.6g}"

        # 基本合理性保护：loss 不应超过 baseline（校正后仍超时进行 cap，并保留原始值供前端/排错展示）
        l_cap = min(max(0.0, l_adj), max(0.0, b))
        cur = max(0.0, b - l_cap)
        return {
            "type": "current_holdings",
            "year": year,
            "baseline_area_mu": round(b, 2),
            "loss_area_mu": round(l_cap, 2),
            "area_mu": round(cur, 2),
            "retention_rate": round((cur / b * 100.0) if b > 0 else 100.0, 2),
            "loss_area_mu_raw": round(l_raw, 2),
            "loss_area_mu_adjusted": round(l_adj, 2),
            "loss_adjustment_note": adjust_note or None,
        }

    def trend_cropland_loss(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """逐年夏窗 Sentinel 低 NDVI 与 GL30(2020) 耕地叠加；GL30 面积与 S2 代理流失不可严格相加。"""
        if not isinstance(inputs, dict) or inputs.get("type") != "geometry":
            raise ValueError("trend_cropland_loss requires geometry as input.")
        region = str(params.get("region") or inputs.get("region") or "")
        target = str(params.get("target_object") or "耕地")
        thr = float(params.get("ndvi_threshold", 0.15))
        years_raw = params.get("years")
        if not isinstance(years_raw, list) or not years_raw:
            raise ValueError("trend_cropland_loss requires params.years: non-empty list of int.")
        years = [int(y) for y in years_raw]

        base = self.load_globeland30({"region": region, "target_object": target}, inputs)
        bstat = self.area_stats({"label": "globeland30_baseline_2020"}, base)
        baseline_mu = float(bstat.get("area_mu", 0.0))
        if baseline_mu <= 0:
            logger.warning("trend_cropland_loss: zero baseline area for region=%s", region)

        max_cloud = float(params.get("max_cloud_cover", 40.0))
        scale_m = int(params.get("scale_m", 200))
        download_timeout = int(params.get("download_timeout", 360))
        half_days = int(params.get("date_half_width_days", 40))
        per_year_retries = int(params.get("per_year_retries", 3))
        retry_sleep_s = params.get("retry_sleep_s") or [4.0, 8.0]
        parallel_years = bool(params.get("parallel_years", False))
        parallel_workers = int(params.get("parallel_workers", 2))

        def _compute_year(y: int) -> Dict[str, Any]:
            last_e: Optional[Exception] = None
            st: Optional[Dict[str, Any]] = None
            for attempt in range(per_year_retries):
                try:
                    sat = self.search_satellite(
                        {
                            "region": region,
                            "year": y,
                            "max_cloud_cover": max_cloud,
                            "scale_m": scale_m,
                            "download_timeout": download_timeout,
                            "date_half_width_days": half_days,
                        },
                        inputs,
                    )
                    ndvi = self.calculate_ndvi({}, sat)
                    loss = self.detect_change(
                        {"ndvi_threshold": thr, "export_geojson": False},
                        [base, ndvi, sat],
                    )
                    st = self.area_stats({"label": f"loss_{y}"}, loss)
                    last_e = None
                    break
                except Exception as e:  # noqa: BLE001
                    last_e = e
                    logger.warning(
                        "trend_cropland_loss year=%s attempt=%s: %s",
                        y,
                        attempt + 1,
                        e,
                    )
                    if attempt < per_year_retries - 1:
                        sl = float(retry_sleep_s[min(attempt, len(retry_sleep_s) - 1)] or 4.0)
                        time.sleep(sl)
            if last_e is not None or st is None:
                raise RuntimeError(f"trend_cropland_loss year={y} 在多次重试后仍失败: {last_e!s}")
            loss_mu = float(st.get("area_mu", 0.0))
            row: Dict[str, Any] = {"year": y, "loss_area_mu": round(loss_mu, 2)}
            if baseline_mu > 0:
                row["loss_to_baseline_area_ratio"] = round(loss_mu / baseline_mu, 3)
            if loss_mu <= baseline_mu and baseline_mu > 0:
                row["implied_cropland_not_low_ndvi_proxy_mu"] = round(baseline_mu - loss_mu, 2)
            else:
                row["implied_cropland_not_low_ndvi_proxy_mu"] = 0.0
                if loss_mu > baseline_mu:
                    row["baseline_compare_note"] = "low_ndvi 代理面积(当前分辨率)大于 GL30 基线表面积(30m)时，两者不可相减，仅供参考年份间相对变化。"
            return row

        series: list[dict[str, Any]] = []
        if parallel_years and len(years) >= 2:
            max_workers = max(1, min(parallel_workers, len(years)))
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(_compute_year, y): y for y in years}
                for fut in as_completed(futs):
                    series.append(fut.result())
            series.sort(key=lambda r: int(r.get("year", 0)))
        else:
            for y in years:
                series.append(_compute_year(int(y)))

        prev_loss_mu: Optional[float] = None
        for row in series:
            loss_mu = float(row.get("loss_area_mu") or 0.0)
            if prev_loss_mu is not None:
                row["loss_delta_from_prior_year_mu"] = round(loss_mu - prev_loss_mu, 2)
            prev_loss_mu = loss_mu

        return {
            "type": "trend_result",
            "region": region,
            "target_object": target,
            "ndvi_threshold": thr,
            "globeland_baseline": "2020 (GlobeLand30)",
            "baseline_area_mu": round(baseline_mu, 2),
            "years": years,
            "series": series,
            "model_note": "各年 loss_area 使用同一夏窗+同一套 NDVI/重采样流程，可比较年份间相对变化；"
            "globeland_baseline 为 30m 地类面积，与 Sentinel 代理 loss 无严格可加性。",
        }

    def compliance_check_point(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """点位代理：GL30(2020) 像元类 + 指定年夏窗 NDVI；非执法或红线认定。"""
        use_center = bool(params.get("use_bbox_center"))
        if use_center:
            g = inputs
            if not isinstance(g, dict) or g.get("type") != "geometry":
                raise ValueError("compliance_check_point (bbox center) requires a geometry output dict as input.")
            bb = g["bbox"]
            lon = (float(bb[0]) + float(bb[2])) / 2.0
            lat = (float(bb[1]) + float(bb[3])) / 2.0
            loc_mode = str(params.get("location_mode") or "admin_bbox_center")
        else:
            if not isinstance(inputs, list) or len(inputs) > 0:
                raise ValueError("compliance_check_point 使用坐标时 inputs 需为 [] 且提供 params.lon/lat。")
            lon = float(params.get("lon"))
            lat = float(params.get("lat"))
            loc_mode = str(params.get("location_mode") or "coordinates")

        target = str(params.get("target_object") or "耕地")
        year = int(params.get("year", datetime.now().year))
        thr = float(params.get("ndvi_threshold", 0.15))
        yfg_proxy = "基本农田" in target

        if yfg_proxy:
            class_codes = CLASS_MAPPING.get("耕地", (10, 11, 12))
        else:
            class_codes = CLASS_MAPPING.get(target, (10, 11, 12))

        pad = 0.002
        bbox = [lon - pad, lat - pad, lon + pad, lat + pad]
        tile_names = self._unpacker.get_tile_names_from_bbox(bbox)
        gl_value: Optional[int] = None
        for tile in tile_names or []:
            tif_path = self._unpacker.unpack_tile(tile)
            if not tif_path:
                continue
            with rasterio.open(tif_path) as src:
                xs, ys = warp_transform("EPSG:4326", src.crs, [lon], [lat])
                row, col = src.index(xs[0], ys[0])
                ri, ci = int(np.floor(float(row))), int(np.floor(float(col)))
                if 0 <= ri < src.height and 0 <= ci < src.width:
                    gl_value = int(src.read(1)[ri, ci])
                    break
        if gl_value is None:
            raise FileNotFoundError("GlobeLand30 无法在该点采样，请检查坐标范围与本地分幅是否齐全。")

        is_gl_target = gl_value in class_codes
        yfg_note: Optional[str] = None
        if yfg_proxy:
            yfg_note = "GlobeLand30 无“永久基本农田”专类，以耕地代码(10/11/12)作空间代理，非管理红线/专项认定。"

        if self._gee_downloader is None:
            self._gee_downloader = GEEDownloader(
                self.gee.cfg.project_id,
                processed_data_dir=self._cfg.processed_data_dir,
                raw_admin_boundary_dir=self._cfg.raw_admin_boundary_dir,
                processed_admin_boundary_dir=self._cfg.processed_admin_boundary_dir,
            )

        dt = datetime(year, 7, 20)
        start = (dt - timedelta(days=20)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=20)).strftime("%Y-%m-%d")
        poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]],
                ]
            ],
        }
        max_cloud = float(params.get("max_cloud_cover", 20.0))
        scale_m = int(params.get("scale_m", 20))
        red, nir, s2_meta = self._gee_downloader.fetch_s2_b4_b8(
            bbox=bbox,
            geometry_geojson=poly,
            start_date=start,
            end_date=end,
            max_cloud_cover=max_cloud,
            scale=scale_m,
        )
        ndvi_arr = (nir - red) / (nir + red + 1e-6)
        h, w = ndvi_arr.shape[0], ndvi_arr.shape[1]
        ndvi_at = float(ndvi_arr[h // 2, w // 2]) if h > 0 and w > 0 else 0.0

        if is_gl_target and ndvi_at > thr + 0.1:
            verdict = f"地类(2020)在「{target}」代理码集合内，且该年夏窗像元 NDVI 明显偏绿，空间上「倾向」仍有植被/作物，非法律认定。"
        elif is_gl_target and ndvi_at >= thr:
            verdict = f"地类(2020)在「{target}」代理集内，NDVI 仅略高于低植被阈值，可能生长偏弱，非法律认定。"
        elif is_gl_target and ndvi_at < thr:
            verdict = f"地类(2020)在「{target}」代理集内，但该年夏窗 NDVI 低于阈值，可能非粮/撂荒/建设（遥感代理），非法律认定。"
        else:
            verdict = f"该点 GL30(2020) 像元值为 {gl_value}，不落在「{target}」代理码集合上。"

        return {
            "type": "compliance_result",
            "location_mode": loc_mode,
            "lon": round(lon, 6),
            "lat": round(lat, 6),
            "target_object": target,
            "globeland30_value": gl_value,
            "globeland30_is_target_proxy": is_gl_target,
            "summer_window_year": year,
            "s2_sample_ndvi": round(ndvi_at, 4),
            "s2_meta": {k: s2_meta.get(k) for k in ("acquired", "cloud_cover", "scale_m", "scene_id") if s2_meta and k in s2_meta} if s2_meta else {},
            "ndvi_threshold_reference": thr,
            "yongjiu_farmland_proxy_note": yfg_note,
            "verdict": verdict,
        }

    def region_compare_baseline(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """多行政区 GlobeLand30(2020) 目标地类面积（亩）横向对比。"""
        if inputs not in ([], (), None):
            raise ValueError("region_compare_baseline expects no upstream task inputs (use params.regions).")
        regions = params.get("regions") or []
        if not isinstance(regions, list) or len(regions) < 2:
            raise ValueError("params.regions 至少需要两个行政区名称。")
        target = str(params.get("target_object") or "耕地")
        rows: list[dict[str, Any]] = []
        regs = [str(r) for r in regions[:6]]
        parallel_enabled = bool(params.get("parallel_enabled", True))
        parallel_workers = int(params.get("parallel_workers", 4))

        def _one(rr: str) -> dict[str, Any]:
            g = self.resolve_geometry({"region": rr}, {})
            m = self.load_globeland30({"region": rr, "target_object": target}, g)
            st = self.area_stats({"label": f"gl30_{rr}"}, m)
            return {
                "region": rr,
                "area_mu": st.get("area_mu"),
                "area_hectares": st.get("area_hectares"),
                "area_sqm": st.get("area_sqm"),
                "unit": st.get("unit", "亩"),
            }

        if parallel_enabled and len(regs) >= 2:
            max_workers = max(1, min(parallel_workers, len(regs)))
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(_one, rr): rr for rr in regs}
                for fut in as_completed(futs):
                    rr = futs[fut]
                    try:
                        rows.append(fut.result())
                    except Exception as e:
                        logger.exception("region_compare_baseline failed for region=%s", rr)
                        rows.append({"region": rr, "error": str(e)})
        else:
            for rr in regs:
                try:
                    rows.append(_one(rr))
                except Exception as e:
                    logger.exception("region_compare_baseline failed for region=%s", rr)
                    rows.append({"region": rr, "error": str(e)})

        ok = [x for x in rows if "error" not in x]
        summary: Optional[dict[str, Any]] = None
        if len(ok) >= 2:
            by_mu = sorted(ok, key=lambda x: float(x.get("area_mu") or 0.0), reverse=True)
            hi, lo = by_mu[0], by_mu[-1]
            summary = {
                "largest": {"region": hi["region"], "area_mu": hi.get("area_mu")},
                "smallest": {"region": lo["region"], "area_mu": lo.get("area_mu")},
            }
        return {
            "type": "region_compare_result",
            "metric": "globeland30_2020_baseline",
            "target_object": target,
            "model_note": "各行政区 GL30(2020) 掩膜下目标地类面积，边界来自 GEE/GAUL，与官方调查口径可能不一致。",
            "summary": summary,
            "rows": rows,
        }

    @staticmethod
    def _aff_from_gis(val: Any) -> Affine:
        if isinstance(val, Affine):
            return val
        if isinstance(val, (list, tuple)) and len(val) >= 6:
            return Affine(*[float(x) for x in val[:6]])
        raise TypeError("dst_transform must be Affine or 6-tuple of floats")

    def _save_gee_download_to_tif(self, url: str, tif_path: str) -> None:
        if os.path.exists(tif_path):
            return
        import requests
        from io import BytesIO
        import zipfile

        os.makedirs(os.path.dirname(tif_path) or ".", exist_ok=True)
        resp = requests.get(url, timeout=300)
        resp.raise_for_status()
        content = resp.content
        if content[:2] == b"PK":
            z = zipfile.ZipFile(BytesIO(content))
            tif_names = [n for n in z.namelist() if n.lower().endswith((".tif", ".tiff"))]
            if not tif_names:
                raise RuntimeError("GEE 下载的 ZIP 中无 TIFF。")
            with z.open(tif_names[0]) as src, open(tif_path, "wb") as dst:
                dst.write(src.read())
        elif content[:4] in (b"II*\x00", b"MM\x00*"):
            with open(tif_path, "wb") as f:
                f.write(content)
        else:
            raise RuntimeError("GEE 返回非 TIFF/ZIP 内容。")

    def _download_esa_worldcover_tif(
        self,
        geometry_geojson: Dict[str, Any],
        dest_path: str,
        scale_m: int,
    ) -> str:
        ee = self.gee.ee
        region = self.gee.geometry_from_geojson(geometry_geojson)
        img, _yr = self.gee.worldcover_image_for_year(2021)
        im = ee.Image(img).clip(region)
        url = im.getDownloadURL(
            {
                "region": region,
                "scale": int(scale_m),
                "crs": "EPSG:3857",
                "format": "GEO_TIFF",
            }
        )
        self._save_gee_download_to_tif(url, dest_path)
        return dest_path

    def land_transfer_after_loss(self, params: Dict[str, Any], inputs: Any) -> Dict[str, Any]:
        """在 GL30 耕地 ∩ 低 NDVI 流失像元上，统计重投影到流失栅格的 ESA WorldCover(v200) 类别计数。"""
        if not isinstance(inputs, dict) or inputs.get("type") != "geometry":
            raise ValueError("land_transfer_after_loss requires geometry as input.")
        region = str(params.get("region") or inputs.get("region") or "")
        year = int(params.get("year") or datetime.now().year)
        target = str(params.get("target_object") or "耕地")
        thr = float(params.get("ndvi_threshold", 0.15))

        g = self.load_globeland30({"region": region, "target_object": target}, inputs)
        sat = self.search_satellite({"region": region, "year": year, "max_cloud_cover": 20.0}, inputs)
        ndv = self.calculate_ndvi({}, sat)
        loss_res = self.detect_change(
            {"ndvi_threshold": thr, "export_geojson": False},
            [g, ndv, sat],
        )
        m = loss_res.get("mask")
        if m is None or m.size == 0 or int(np.sum(m)) == 0:
            return {
                "type": "transfer_result",
                "reliability": "proxy",
                "target_object": target,
                "ndvi_summer_year": year,
                "ndvi_threshold": thr,
                "loss_area_mu": 0.0,
                "loss_pixels": 0,
                "worldcover": {"source": "ESA/WorldCover/v200 (GEE)", "reproject_scale_m": None},
                "transfer_matrix": [],
                "main_direction": "",
                "conclusion": "未检测到与阈值一致的低 NDVI 代理流失像元。",
                "model_note": "流失=GL30(2020)耕地与当年夏窗 NDVI<阈值的交叠。",
            }

        pa = float(loss_res.get("pixel_area_sqm", 0.0) or 0.0)
        h, w = m.shape[0], m.shape[1]
        loss_px = int(np.sum(m > 0))
        loss_mu = loss_px * pa / 666.66666667

        bbox = inputs["bbox"]
        bbox_area_deg2 = max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        scale_wc = 200 if bbox_area_deg2 > 1.0 else 30
        tif_p = os.path.join(self._cfg.processed_data_dir, "gee", f"esa_wc_v200_tr_{int(time.time())}.tif")
        self._download_esa_worldcover_tif(inputs["geometry_geojson"], tif_p, scale_wc)

        dst_aff = self._aff_from_gis(loss_res.get("dst_transform"))
        dst_crs = CRS.from_string(str(loss_res.get("dst_crs", "EPSG:3857")))

        wc_dst = np.zeros((h, w), dtype=np.uint8)
        with rasterio.open(tif_p) as src:
            src_arr = src.read(1, masked=True)
            src_arr = np.array(src_arr.filled(0), dtype=np.uint8)
            reproject(
                source=src_arr,
                destination=wc_dst,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=0,
                dst_transform=dst_aff,
                dst_crs=dst_crs,
                resampling=Resampling.nearest,
            )

        lo = m > 0
        codes = wc_dst[lo]
        if codes.size == 0:
            raise RuntimeError("内部错误：有流失掩膜但无 WorldCover 采样。")

        esa_labels: Dict[int, str] = {
            0: "无数据/背景",
            10: "林地",
            20: "灌木地",
            30: "草地",
            40: "耕地",
            50: "建筑区",
            60: "裸地",
            70: "水体",
            80: "雪/冰",
            90: "草本/湿地",
            95: "红树林",
            100: "苔藓/地衣",
        }

        rows: list[dict[str, Any]] = []
        for c in np.unique(codes).tolist():
            cc = int(c)
            cnt = int(np.sum(codes == c))
            amu = cnt * pa / 666.66666667
            pct = (cnt / float(loss_px) * 100.0) if loss_px else 0.0
            rows.append(
                {
                    "to_class": esa_labels.get(cc, f"ESA码{cc}"),
                    "esa_code": cc,
                    "area_mu": round(amu, 2),
                    "percentage": round(pct, 2),
                    "description": f"在流失代理像元上，WorldCover 值 {cc}",
                }
            )
        rows.sort(key=lambda r: r["area_mu"], reverse=True)
        top = rows[0] if rows else None
        main = ""
        if top:
            if int(top.get("esa_code", -1)) == 40:
                main = f"在流失像元上 WorldCover 仍以「耕地」类为主，约占流失像元的 {top['percentage']:.1f}%"
            else:
                main = f"流失代理下主要 WorldCover 类为「{top['to_class']}」({top['percentage']:.1f}%)"
        concl = (
            f"在{year} 年夏窗、NDVI<{thr} 的 GL30(2020) 耕地代理流失范围内，"
            f"以 ESA WorldCover（重采样到流失栅格）统计，{main}。"
        )

        return {
            "type": "transfer_result",
            "reliability": "proxy_esa_wc",
            "target_object": target,
            "ndvi_summer_year": year,
            "ndvi_threshold": thr,
            "loss_area_mu": round(loss_mu, 2),
            "loss_pixels": loss_px,
            "worldcover": {
                "source": "ESA/WorldCover/v200 (GEE)",
                "reproject_scale_m": scale_wc,
            },
            "transfer_matrix": rows,
            "main_direction": main,
            "conclusion": concl,
            "model_note": "流失为遥感代理；WorldCover 与 Sentinel 时相/分辨率经重采样，非地籍认定。",
        }

