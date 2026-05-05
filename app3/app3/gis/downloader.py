"""
数据获取与下载模块（MVP）。

- 遥感影像：通过 Google Earth Engine (GEE) 获取 Sentinel-2 SR，并下载为 GeoTIFF。
- 行政区边界：通过 geoBoundaries（gbOpen）下载/解压到本地目录，并在进程内缓存 GeoDataFrame 以便重复查询。
"""

import os
import requests
import logging
import zipfile
import math
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential
from app3.gis.config_paths import (
    PROCESSED_DATA_DIR,
    RAW_ADMIN_BOUNDARY_DIR,
    PROCESSED_ADMIN_BOUNDARY_DIR,
)

# 设置本模块的日志记录器
logger = logging.getLogger(__name__)


def _safe_strip(value: Any) -> str:
    """
    统一的文本清洗：容忍 NaN/float/None，避免出现 `'float' object has no attribute 'strip'`。
    """
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()

class GEEDownloader:
    """
    Google Earth Engine 遥感数据获取器。
    """

    def __init__(self, project_id: str):
        if not project_id:
            raise ValueError("GEE_PROJECT_ID 为空，无法初始化 Earth Engine。")
        self.project_id = project_id
        
        try:
            import ee  # type: ignore
            self.ee = ee
            # 必须成功初始化，不再支持 Mock
            self.ee.Initialize(project=self.project_id)
            logger.info(f"GEE 初始化成功 (Project: {self.project_id})")
        except Exception as e:
            logger.error(f"GEE 初始化失败: {e}")
            raise RuntimeError(f"Earth Engine 初始化失败，请检查项目 ID、认证状态或网络连接: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def fetch_s2_b4_b8(
        self,
        bbox: List[float],
        start_date: str,
        end_date: str,
        geometry_geojson: Optional[Dict[str, Any]] = None,
        max_cloud_cover: float = 20.0,
        scale: int = 20,
        export_crs: str = "EPSG:3857",
        output_dir: Optional[str] = None,
        download_timeout: int = 300,
    ) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        从 GEE 拉取 Sentinel-2 SR（HARMONIZED）B4/B8 波段。
        """
        import numpy as np
        import rasterio

        if geometry_geojson:
            region = self.ee.Geometry(geometry_geojson, None, False)
        else:
            region = self.ee.Geometry.Rectangle(bbox, proj="EPSG:4326", geodesic=False)
        def _collection(mc: float):
            return (
                self.ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(region)
                .filterDate(start_date, end_date)
                .filter(self.ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", mc))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )

        col = _collection(max_cloud_cover)
        image = col.first()
        if image is None:
            raise RuntimeError("GEE 未返回影像对象（可能是查询条件过严或权限问题）。")

        size = int(col.size().getInfo())
        if size <= 0 and max_cloud_cover < 80.0:
            looser = min(80.0, max(max_cloud_cover + 20.0, 55.0))
            col = _collection(looser)
            image = col.first()
            size = int(col.size().getInfo())
        if size <= 0:
            # 仍无景时：该年 4–10 月宽窗 + 高云量（应对个别地区夏窗极云年）
            y = int(str(start_date)[:4])
            col = (
                self.ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(region)
                .filterDate(f"{y}-04-01", f"{y}-10-31")
                .filter(self.ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 90.0))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )
            image = col.first()
            size = int(col.size().getInfo())
        if size <= 0:
            raise RuntimeError(
                "GEE 未找到符合条件的 Sentinel-2 影像。请放宽时间范围/云量阈值或缩小 AOI。"
            )

        product_id = image.get("PRODUCT_ID").getInfo() or image.get("system:index").getInfo() or "unknown"
        cloud = float(image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo() or 0.0)
        time_start = image.get("system:time_start").getInfo()
        acquired = datetime.utcfromtimestamp(int(time_start) / 1000).strftime("%Y-%m-%d") if time_start else None

        bands = image.select(["B4", "B8"])
        params = {
            "region": region,
            "scale": scale,
            "format": "GEO_TIFF",
            "crs": export_crs,
        }
        url = bands.getDownloadURL(params)

        output_dir = output_dir or os.path.join(PROCESSED_DATA_DIR, "gee")
        os.makedirs(output_dir, exist_ok=True)
        safe_id = str(product_id).replace("/", "_").replace(":", "_")
        tif_path = os.path.join(output_dir, f"s2_{safe_id}_B4_B8_{scale}m.tif")

        if not os.path.exists(tif_path):
            try:
                resp = requests.get(url, timeout=download_timeout)
                resp.raise_for_status()
            except Exception as e:
                raise RuntimeError(
                    f"GEE 影像下载失败 (HTTP/网络，timeout={download_timeout}s, scale={scale}m, scene={product_id!s}): {e}"
                ) from e
            content = resp.content
            if content[:2] == b"PK":
                z = zipfile.ZipFile(BytesIO(content))
                tif_names = [n for n in z.namelist() if n.lower().endswith((".tif", ".tiff"))]
                if not tif_names:
                    raise RuntimeError("GEE 下载结果中未包含 TIFF 文件。")
                with z.open(tif_names[0]) as src, open(tif_path, "wb") as dst:
                    dst.write(src.read())
            elif content[:4] in (b"II*\x00", b"MM\x00*"):
                with open(tif_path, "wb") as f:
                    f.write(content)
            else:
                snippet = content[:300].decode("utf-8", errors="replace")
                raise RuntimeError(f"GEE 下载结果不是 ZIP/TIFF，可能是错误页面或限流信息: {snippet}")

        with rasterio.open(tif_path) as src:
            red = src.read(1)
            nir = src.read(2)

        meta = {
            "source": "Google Earth Engine (Sentinel-2 SR)",
            "scene_id": product_id,
            "acquired": acquired,
            "cloud_cover": cloud,
            "scale_m": scale,
            "bbox": bbox,
            "tif_path": tif_path,
        }
        return red.astype(np.float32), nir.astype(np.float32), meta


class GeoBoundariesDownloader:
    """
    geoBoundaries 行政区边界下载器（gbOpen）。

    通过 API 获取 ADM0/ADM1/ADM2/ADM3 的下载链接，并落盘保存：
    - 原始 zip: data/raw/admin_boundaries/geoboundaries/gbOpen/{ISO}/{ADM}.zip
    - 解压目录: data/processed/admin_boundaries/geoboundaries/gbOpen/{ISO}/{ADM}/
    """

    def __init__(self, release: str = "gbOpen"):
        self.release = release
        self.api_base = "https://www.geoboundaries.org/api/current"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _ensure_dirs(self, iso3: str, adm_level: str) -> Tuple[str, str]:
        zip_dir = os.path.join(RAW_ADMIN_BOUNDARY_DIR, "geoboundaries", self.release, iso3)
        extract_dir = os.path.join(PROCESSED_ADMIN_BOUNDARY_DIR, "geoboundaries", self.release, iso3, adm_level)
        os.makedirs(zip_dir, exist_ok=True)
        os.makedirs(extract_dir, exist_ok=True)
        zip_path = os.path.join(zip_dir, f"{adm_level}.zip")
        return zip_path, extract_dir

    def _get_metadata(self, iso3: str, adm_level: str) -> Dict[str, Any]:
        url = f"{self.api_base}/{self.release}/{iso3}/{adm_level}/"
        resp = self.session.get(url, timeout=60)
        resp.raise_for_status()
        meta = resp.json()
        if isinstance(meta, list):
            if not meta:
                raise RuntimeError(f"geoBoundaries API 返回空列表: {url}")
            return meta[0]
        if isinstance(meta, dict):
            return meta
        raise RuntimeError(f"无法解析 geoBoundaries API 响应: {url}")

    def download_and_extract(self, iso3: str, adm_level: str) -> str:
        """
        下载并解压指定层级的边界数据，返回 .shp 文件路径。
        """
        iso3 = iso3.upper()
        adm_level = adm_level.upper()
        zip_path, extract_dir = self._ensure_dirs(iso3, adm_level)

        shp_candidates = []
        for root, _, files in os.walk(extract_dir):
            for f in files:
                if f.lower().endswith(".shp"):
                    shp_candidates.append(os.path.join(root, f))
        if shp_candidates:
            return shp_candidates[0]

        meta = self._get_metadata(iso3, adm_level)
        shp_url = (
            meta.get("shpDownloadURL")
            or meta.get("shpDownloadUrl")
            or meta.get("staticDownloadLink")
        )
        if not shp_url:
            raise RuntimeError(f"geoBoundaries 未提供可用下载链接（{iso3} {adm_level}）")

        if not os.path.exists(zip_path):
            logger.info(f"正在下载 geoBoundaries {iso3} {adm_level}...")
            r = self.session.get(shp_url, timeout=300)
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                f.write(r.content)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        shp_candidates = []
        for root, _, files in os.walk(extract_dir):
            for f in files:
                if f.lower().endswith(".shp"):
                    shp_candidates.append(os.path.join(root, f))
        if not shp_candidates:
            raise RuntimeError(f"解压后未找到 .shp 文件（{iso3} {adm_level}）")

        return shp_candidates[0]


class AdminBoundaryManager:
    """
    行政区边界管理器。
    负责查找、下载和缓存各级行政区划（ADM0-ADM3）的地理边界。
    """

    def __init__(self, iso3: str = "CHN"):
        """
        初始化管理器。

        Args:
            iso3 (str): ISO 3166-1 alpha-3 国家代码，默认 "CHN"。
        """
        import threading
        
        self.iso3 = iso3.upper()
        self.downloader = GeoBoundariesDownloader(release="gbOpen")
        self._gdf_cache: Dict[str, Any] = {}
        self._gdf_cache_lock = threading.Lock()  # 添加锁保护缓存访问
        # level -> { norm_key -> set(original_name_strings) }
        self._name_index_cache: Dict[str, Dict[str, set[str]]] = {}
        self._name_index_lock = threading.Lock()
        self._geocode_session = requests.Session()
        self._geocode_session.headers.update(
            {
                "User-Agent": "farmland-monitoring-mvp/1.0 (admin-boundary-geocoder)",
                "Accept": "application/json",
            }
        )

    def ensure_local_baseline(self) -> Dict[str, str]:
        """确保本地已预置基础行政区划数据。"""
        paths = {}
        for level in ("ADM0", "ADM1", "ADM2"):
            paths[level] = self.downloader.download_and_extract(self.iso3, level)
        return paths

    def _load_level(self, level: str):
        """内部方法：加载指定层级的 GeoDataFrame。"""
        import geopandas as gpd

        level = level.upper()
        
        # 快速检查（无锁）
        if level in self._gdf_cache:
            return self._gdf_cache[level]
        
        # 先检查是否需要加载
        needs_load = False
        with self._gdf_cache_lock:
            if level not in self._gdf_cache:
                needs_load = True
        
        # 如果需要，在锁外加载
        if needs_load:
            shp = self.downloader.download_and_extract(self.iso3, level)
            gdf = gpd.read_file(shp)
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326", allow_override=True)
            else:
                gdf = gdf.to_crs("EPSG:4326")
            
            # 在锁内更新缓存
            with self._gdf_cache_lock:
                if level not in self._gdf_cache:
                    self._gdf_cache[level] = gdf
        
        return self._gdf_cache[level]

    @staticmethod
    def _normalize_region_name(name: str) -> str:
        """移除行政区划后缀（如“省”、“市”），便于模糊匹配。"""
        s = _safe_strip(name)
        suffixes = (
            "特别行政区", "自治区", "自治州", "自治县", "地区", 
            "盟", "省", "市", "区", "县", "旗",
        )
        changed = True
        while changed:
            changed = False
            for suf in suffixes:
                if s.endswith(suf) and len(s) > len(suf):
                    s = s[: -len(suf)]
                    changed = True
        return s

    @staticmethod
    def _norm_key(name: str) -> str:
        """
        将名称归一为用于索引的 key：
        - strip + lower
        - 去掉空白与常见分隔符（便于匹配如 "Hong Kong" / "Hong-Kong"）
        - 中文输入保持原字符（仅做 trim），不做繁简转换
        """
        s = _safe_strip(name).lower()
        for ch in (" ", "\t", "\n", "\r", "-", "_", ".", ",", "，", "（", "）", "(", ")", "[", "]"):
            s = s.replace(ch, "")
        return s

    @staticmethod
    def _admin_search_candidates(region: str) -> List[str]:
        """
        生成用于边界匹配的候选名称。
        经验：区市连写（如“成都市郫都区”）时，数据源可能只包含“郫都区”，因此补充短名候选。
        """
        import re

        s = _safe_strip(region)
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

    def _get_pinyin_variants(self, name: str) -> List[str]:
        """获取中文名称的拼音变体（用于匹配 geoBoundaries 的拼音命名）。"""
        if self.iso3 != "CHN":
            return []
        try:
            from pypinyin import pinyin, Style
            norm = self._normalize_region_name(name)
            # 生成全拼，不带声调，首字母大写或全小写
            py_list = pinyin(norm, style=Style.NORMAL)
            full_py = "".join([item[0] for item in py_list])
            
            variants = [
                full_py.capitalize(),
                full_py.lower(),
                full_py,
            ]
            variants.append(f"{full_py.capitalize()}shi")
            variants.append(f"{full_py.capitalize()} Shi")
            return list(set(variants))
        except ImportError:
            return []

    def _china_aliases(self, name: str) -> List[str]:
        """
        将常见中文省级/直辖市名称映射到 geoBoundaries（ADM1）中常见的英文命名。
        目的：避免 geoBoundaries 的 shapeName 为英文导致无法匹配中文输入。
        """
        if self.iso3 != "CHN":
            return []

        n = self._normalize_region_name(name)
        # 仅保留“pypinyin 不能直接覆盖/容易歧义”的少数别名；
        # 常见省份优先依赖数据集自身字段 + 拼音候选来命中，减少硬编码维护成本。
        mapping = {
            "北京": ["Beijing", "Beijing Municipality"],
            "天津": ["Tianjin", "Tianjin Municipality"],
            "上海": ["Shanghai", "Shanghai Municipality"],
            "重庆": ["Chongqing", "Chongqing Municipality"],
            "黑龙江": ["Heilongjiang"],
            # 两个山西/陕西易混：geoBoundaries 常用 Shaanxi
            "陕西": ["Shaanxi", "Shaanxi Province"],
            "台湾": ["Taiwan"],
            "内蒙古": ["Inner Mongolia", "Inner Mongolia Autonomous Region"],
            "广西": ["Guangxi", "Guangxi Zhuang Autonomous Region"],
            "西藏": ["Tibet", "Xizang", "Tibet Autonomous Region"],
            "宁夏": ["Ningxia", "Ningxia Hui Autonomous Region"],
            "新疆": ["Xinjiang", "Xinjiang Uygur Autonomous Region"],
            "香港": ["Hong Kong", "Hong Kong SAR", "Hong Kong Special Administrative Region"],
            "澳门": ["Macau", "Macao", "Macao SAR", "Macau SAR"],
        }
        return mapping.get(n, [])

    def _name_candidates(self, region_name: str) -> List[str]:
        raw = _safe_strip(region_name)
        if not raw:
            return []
        norm = self._normalize_region_name(raw)
        aliases = self._china_aliases(raw)
        pinyin_variants = self._get_pinyin_variants(raw)
        # 补充“市区连写”的短名候选（raw/norm 可能仍是全名）
        admin_cands = self._admin_search_candidates(raw)
        out: List[str] = []
        for x in [raw, norm, *admin_cands, *aliases, *pinyin_variants]:
            x = _safe_strip(x)
            if x and x not in out:
                out.append(x)
        return out

    def _build_name_index(self, level: str, gdf) -> Dict[str, set[str]]:
        """
        为某个层级构建 name 索引：norm_key(name) -> {原始 name 值集合}
        用于避免每次都在所有列上做 N 次全表扫描。
        """
        cols = self._pick_name_columns(gdf)
        idx: Dict[str, set[str]] = {}
        for c in cols:
            try:
                series = gdf[c].astype(str)
            except Exception:
                continue
            for v in series.tolist():
                s = _safe_strip(v)
                if not s:
                    continue
                k = self._norm_key(s)
                if not k:
                    continue
                bucket = idx.get(k)
                if bucket is None:
                    idx[k] = {s}
                else:
                    bucket.add(s)
        return idx

    def _get_name_index(self, level: str, gdf) -> Dict[str, set[str]]:
        level = level.upper()
        if level in self._name_index_cache:
            return self._name_index_cache[level]
        with self._name_index_lock:
            if level in self._name_index_cache:
                return self._name_index_cache[level]
        built = self._build_name_index(level, gdf)
        with self._name_index_lock:
            self._name_index_cache.setdefault(level, built)
            return self._name_index_cache[level]

    @staticmethod
    def _pick_name_columns(gdf) -> List[str]:
        cols = []
        for c in gdf.columns:
            if c == "geometry":
                continue
            if str(c).lower().find("name") >= 0 or str(c).lower().find("shapename") >= 0:
                cols.append(c)
        if cols:
            return cols
        return [c for c in gdf.columns if c != "geometry" and gdf[c].dtype == object]

    def find_geometry(self, region_name: str, prefer_level: Optional[str] = None) -> Dict[str, Any]:
        """
        根据区域名查找边界 geometry。
        """
        import re

        raw = _safe_strip(region_name)
        candidates = self._name_candidates(raw)

        def _default_level_order(name: str) -> List[str]:
            """
            根据中文后缀粗略判断行政层级，优先尝试更可能命中的 level。
            - 区/县/旗/盟/州：更像 ADM3
            - 市：更像 ADM2
            - 省/自治区/直辖市/特别行政区：更像 ADM1
            """
            s = _safe_strip(name)
            if re.search(r"(区|县|旗|盟|州|自治州|自治县)$", s):
                return ["ADM3", "ADM2", "ADM1"]
            if s.endswith("市"):
                return ["ADM2", "ADM1", "ADM3"]
            if re.search(r"(省|自治区|特别行政区)$", s) or s in ("北京", "上海", "天津", "重庆"):
                return ["ADM1", "ADM2", "ADM3"]
            return ["ADM1", "ADM2", "ADM3"]

        levels: List[str] = []
        if prefer_level:
            levels.append(prefer_level.upper())
        levels.extend(_default_level_order(raw))
        seen = set()
        ordered = []
        for lv in levels:
            if lv not in seen:
                ordered.append(lv)
                seen.add(lv)

        # 市+区县连写的常见输入：先定位“市”边界，再在其内部筛 ADM3，降低同名误匹配
        city_geom = None
        city_only = None
        m_city = re.match(r"^(.+?市)([\u4e00-\u9fff]+(?:区|县|旗|盟|州|自治[州县]))$", raw)
        if m_city:
            city_only = m_city.group(1)

        # 预先求 city_geom（若能唯一命中），用于后续 ADM3 过滤
        if city_only:
            try:
                # 优先 ADM2 再 ADM1（市通常在 ADM2）
                for lv in ("ADM2", "ADM1"):
                    gdf_city = self._load_level(lv)
                    cols_city = self._pick_name_columns(gdf_city)
                    idx_city = self._get_name_index(lv, gdf_city)
                    # 临时：用本层索引（避免全表扫）
                    hit_names = idx_city.get(self._norm_key(city_only)) or set()
                    row = None
                    for hn in hit_names:
                        mask = None
                        for c in cols_city:
                            try:
                                s = gdf_city[c].astype(str)
                                m = (s == hn)
                            except Exception:
                                continue
                            mask = m if mask is None else (mask | m)
                        if mask is None:
                            continue
                        exact = gdf_city[mask]
                        if len(exact) == 1:
                            row = exact.iloc[0]
                            break
                    if row is not None:
                        city_geom = row.geometry
                        break
            except Exception:
                city_geom = None

        for level in ordered:
            # 注意：名称索引必须基于“完整层级数据”构建并缓存。
            # 若在这里对 gdf 做空间过滤后再建索引，会把“子集索引”缓存为整层索引，影响后续查询命中率。
            gdf_full = self._load_level(level)
            cols = self._pick_name_columns(gdf_full)
            index = self._get_name_index(level, gdf_full)

            gdf = gdf_full
            # 若是 ADM3 且 city_geom 可用：先做空间过滤，减少同名多条导致“非唯一命中”
            if level.upper() == "ADM3" and city_geom is not None:
                try:
                    gdf = gdf[gdf.intersects(city_geom)]
                except Exception:
                    pass
            # 1) 索引化精确命中：candidate -> norm_key -> {可能的原始 name 值} -> 在 cols 上精确匹配
            for cand in candidates:
                ks = self._norm_key(cand)
                if not ks:
                    continue
                hit_names = index.get(ks) or set()
                for hn in hit_names:
                    # 在所有 name 列上做“等值命中”，避免只看某一列漏命中
                    mask = None
                    for c in cols:
                        try:
                            s = gdf[c].astype(str)
                            m = (s == hn)
                        except Exception:
                            continue
                        mask = m if mask is None else (mask | m)
                    if mask is None:
                        continue
                    exact = gdf[mask]
                    if len(exact) == 1:
                        geom = exact.iloc[0].geometry
                        return {"level": level, "name": hn, "geometry": geom, "bbox": list(geom.bounds)}

            # 2) 兜底：contains（仍仅在唯一命中时使用，避免误匹配）
            for c in cols:
                try:
                    series = gdf[c].astype(str)
                except Exception:
                    continue
                for cand in candidates:
                    if not cand:
                        continue
                    contains = gdf[series.str.contains(cand, case=False, na=False)]
                    if len(contains) == 1:
                        geom = contains.iloc[0].geometry
                        return {"level": level, "name": cand, "geometry": geom, "bbox": list(geom.bounds)}

        point = self._geocode_point_wgs84(region_name)
        if point is not None:
            from shapely.geometry import Point

            pt = Point(point[0], point[1])
            for level in ordered:
                gdf = self._load_level(level)
                hits = gdf[gdf.contains(pt)]
                if len(hits) >= 1:
                    geom = hits.iloc[0].geometry
                    return {"level": level, "name": region_name, "geometry": geom, "bbox": list(geom.bounds)}

        raise RuntimeError(f"未能在行政边界数据中匹配到区域: {region_name}")

    def get_children(self, region_name: str) -> List[str]:
        """
        获取指定区域的下级行政区列表。

        Args:
            region_name (str): 父区域名称

        Returns:
            List[str]: 子区域名称列表
        """
        try:
            # 首先找到父区域
            parent = self.find_geometry(region_name)
            parent_level = parent.get("level", "ADM1")
            
            # 确定要查找的子层级
            level_map = {
                "ADM0": "ADM1",  # 国家下的省/州
                "ADM1": "ADM2",  # 省下的市/县
                "ADM2": "ADM3",  # 市下的区县
            }
            child_level = level_map.get(parent_level)
            
            if not child_level:
                logger.warning(f"无法确定 {region_name} ({parent_level}) 的子层级")
                return []
            
            # 加载子层级数据
            try:
                child_gdf = self._load_level(child_level)
            except Exception:
                logger.warning(f"子层级 {child_level} 数据不可用")
                return []
            
            # 获取父区域的几何
            parent_geom = parent.get("geometry")
            if not parent_geom:
                return []
            
            cols = self._pick_name_columns(child_gdf)

            # 先用 bbox 预过滤，显著减少候选数量（纯加速，不改变集合语义）
            try:
                minx, miny, maxx, maxy = parent_geom.bounds
                child_gdf = child_gdf.cx[minx:maxx, miny:maxy]
            except Exception:
                pass

            # 优先使用 GeoPandas 空间索引（若环境支持），否则退化为向量化 intersects
            try:
                sidx = child_gdf.sindex  # noqa: F841
                # 用 bbox 候选再做精确相交判断
                bbox = parent_geom.bounds
                cand_idx = list(child_gdf.sindex.intersection(bbox))
                cand = child_gdf.iloc[cand_idx] if cand_idx else child_gdf.iloc[0:0]
                mask = cand.intersects(parent_geom) | cand.within(parent_geom)
                hits = cand[mask]
            except Exception:
                try:
                    mask = child_gdf.intersects(parent_geom) | child_gdf.within(parent_geom)
                    hits = child_gdf[mask]
                except Exception:
                    return []

            child_names: List[str] = []
            for _, row in hits.iterrows():
                name = None
                for c in cols:
                    val = row.get(c)
                    if val and str(val).strip():
                        name = str(val).strip()
                        break
                if name:
                    child_names.append(name)

            return list(dict.fromkeys(child_names))
            
        except Exception as e:
            logger.warning(f"获取 {region_name} 的子区域失败: {e}")
            return []

    def _geocode_point_wgs84(self, query: str) -> Optional[Tuple[float, float]]:
        """
        使用 Nominatim 将地名解析为 WGS84 坐标点。
        返回 (lon, lat)。
        """
        q = _safe_strip(query)
        if not q:
            return None
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"format": "json", "q": q, "limit": 1}
            resp = self._geocode_session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None
            lon = float(data[0]["lon"])
            lat = float(data[0]["lat"])
            return (lon, lat)
        except Exception:
            return None



