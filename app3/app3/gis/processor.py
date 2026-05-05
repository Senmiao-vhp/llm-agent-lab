"""
GlobeLand30 数据处理模块。
负责加载土地覆盖栅格数据，并根据特定类别（如耕地）提取空间掩膜。
"""

import os
import logging
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, transform_geom, reproject, Resampling
from rasterio.windows import Window
from rasterio.features import geometry_mask, shapes
from typing import Tuple, Optional, List, Dict, Any, Union
from app3.gis.config_paths import FARMLAND_CLASS_CODE, FARMLAND_CLASS_CODES, CRS_DEFAULT

# 设置本模块的日志记录器
logger = logging.getLogger(__name__)

# GlobeLand30 类别映射
CLASS_MAPPING = {
    "耕地": (10, 11, 12),
    "林地": (20,),
    "草地": (30,),
    "灌木地": (40,),
    "湿地": (50,),
    "水体": (60,),
    "人造地表": (80,),
    "裸地": (90,),
    "冰雪": (100,),
}

class GisProcessor:
    """
    通用 GIS 影像处理器。
    负责栅格对齐、重投影、变化检测核心计算及矢量转换。
    """

    @staticmethod
    def align_and_detect(
        ndvi: np.ndarray,
        mask_pieces: Optional[List[Dict[str, Any]]],
        mask_data: Optional[np.ndarray],
        raster_meta: Dict[str, Any],
        ndvi_threshold: float,
        boundary_geojson: Optional[Dict[str, Any]] = None,
        export_geojson: bool = False,
        max_features: int = 2000,
        min_feature_area_pixels: int = 0,
    ) -> Dict[str, Any]:
        """
        执行栅格对齐并识别变化区域。

        Args:
            ndvi (np.ndarray): 已计算的 NDVI 数组。
            mask_pieces: 来自 GlobeLand30 的分块掩膜列表。
            mask_data: 单个完整的掩膜数据。
            raster_meta: 目标影像的元数据。
            ndvi_threshold: 变化检测阈值。
            boundary_geojson: 行政边界。
            export_geojson: 是否输出矢量格式。
            max_features: 矢量化最大要素数量。

        Returns:
            Dict[str, Any]: 包含变化掩膜、变换参数和（可选）矢量数据的字典。
        """
        tif_path = raster_meta.get("tif_path")
        if not tif_path:
            raise ValueError("缺少影像 tif_path，无法进行对齐。")

        try:
            with rasterio.open(tif_path) as dst_src:
                dst_crs = dst_src.crs
                dst_transform = dst_src.transform
                dst_h, dst_w = dst_src.height, dst_src.width
                resx, resy = dst_src.res

            # 1. 调整 NDVI 尺寸（对齐像素偏差）
            if ndvi.shape[0] != dst_h or ndvi.shape[1] != dst_w:
                logger.debug(f"NDVI 尺寸 ({ndvi.shape}) 与影像尺寸 ({dst_h}, {dst_w}) 不符，进行裁剪。")
                h = min(ndvi.shape[0], dst_h)
                w = min(ndvi.shape[1], dst_w)
                ndvi = ndvi[:h, :w]
                dst_h, dst_w = h, w

            # 2. 合并并重投影基准掩膜
            base_mask_on_dst = np.zeros((dst_h, dst_w), dtype=np.uint8)

            if mask_pieces:
                for piece in mask_pieces:
                    src_mask = piece["mask"].astype(np.uint8)
                    src_profile = piece["profile"]
                    tmp = np.zeros((dst_h, dst_w), dtype=np.uint8)
                    reproject(
                        source=src_mask,
                        destination=tmp,
                        src_transform=src_profile["transform"],
                        src_crs=src_profile["crs"],
                        dst_transform=dst_transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.nearest,
                    )
                    base_mask_on_dst = np.maximum(base_mask_on_dst, tmp)
            elif mask_data is not None:
                # 检查 mask_data 尺寸是否匹配
                if mask_data.shape[0] != dst_h or mask_data.shape[1] != dst_w:
                    logger.warning(f"mask_data 尺寸 ({mask_data.shape}) 与目标尺寸 ({dst_h}, {dst_w}) 不一致。")
                    h = min(mask_data.shape[0], dst_h)
                    w = min(mask_data.shape[1], dst_w)
                    mask_data = mask_data[:h, :w]
                base_mask_on_dst = (mask_data == 1).astype(np.uint8)
            else:
                raise ValueError("缺少必要输入 mask（mask_data 或 mask_pieces）。")

            # 3. 核心计算：(是耕地) 且 (NDVI 低于阈值)
            # 使用逻辑运算减少内存开销
            change_mask = (base_mask_on_dst == 1) & (ndvi < ndvi_threshold)

            # 4. 行政边界二次裁剪
            if boundary_geojson:
                geom_in_dst = transform_geom("EPSG:4326", dst_crs, boundary_geojson, precision=6)
                inside_region = geometry_mask(
                    [geom_in_dst],
                    out_shape=(dst_h, dst_w),
                    transform=dst_transform,
                    invert=True,
                    all_touched=False,
                )
                change_mask = change_mask & inside_region

            pixel_area_sqm = float(abs(resx * resy))
            result = {
                "mask": change_mask.astype(np.uint8),
                "pixel_area_sqm": pixel_area_sqm,
                "dst_transform": dst_transform,
                "dst_crs": str(dst_crs)
            }

            # 5. 矢量化（可选）
            if export_geojson:
                features = []
                mask_u8 = change_mask.astype(np.uint8)
                if min_feature_area_pixels and min_feature_area_pixels > 1:
                    try:
                        from rasterio.features import sieve

                        mask_u8 = sieve(mask_u8, size=int(min_feature_area_pixels))
                    except Exception as e:
                        logger.warning(f"sieve 过滤小斑块失败，将跳过。err={e!s}")
                # 仅对值为 1 的区域进行矢量化
                for geom, val in shapes(mask_u8, mask=mask_u8, transform=dst_transform):
                    if int(val) != 1: continue
                    geom_wgs84 = transform_geom(dst_crs, "EPSG:4326", geom, precision=6)
                    features.append({"type": "Feature", "properties": {}, "geometry": geom_wgs84})
                    if len(features) >= max_features:
                        logger.warning(f"矢量化要素数量达到上限 ({max_features})，已截断。")
                        break
                
                result["change_geojson"] = {"type": "FeatureCollection", "features": features}
                result["geojson_truncated"] = len(features) >= max_features

            return result
        except Exception as e:
            logger.error(f"对齐与检测过程中出错: {e}")
            raise

    @staticmethod
    def query_point(
        point_lon: float, 
        point_lat: float,
        mask_pieces: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        查询单个坐标点在掩膜中的类别。
        
        Args:
            point_lon: 经度
            point_lat: 纬度
            mask_pieces: 掩膜分块列表
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            for piece in mask_pieces:
                mask = piece["mask"]
                profile = piece["profile"]
                transform = profile["transform"]
                
                # 计算点在栅格中的位置
                col, row = ~transform * (point_lon, point_lat)
                col, row = int(round(col)), int(round(row))
                
                # 检查点是否在栅格范围内
                if 0 <= row < mask.shape[0] and 0 <= col < mask.shape[1]:
                    # 返回该位置的像素值
                    pixel_val = int(mask[row, col])
                    return {
                        "is_target": pixel_val == 1,
                        "pixel_value": pixel_val,
                        "in_range": True
                    }
            
            # 如果没有任何分块包含该点
            return {
                "is_target": False,
                "in_range": False,
                "pixel_value": None
            }
        except Exception as e:
            logger.error(f"查询点 ({point_lon}, {point_lat}) 时出错: {e}")
            return {
                "is_target": False,
                "in_range": False,
                "error": str(e)
            }

    @staticmethod
    def query_point_on_change_mask(
        point_lon: float, 
        point_lat: float,
        change_mask: np.ndarray,
        dst_transform,
        base_mask: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        查询单个坐标点在变化掩膜中的状态。
        
        Args:
            point_lon: 经度
            point_lat: 纬度
            change_mask: 变化掩膜
            dst_transform: 目标变换
            base_mask: 基准掩膜（可选）
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            # 计算点在栅格中的位置
            col, row = ~dst_transform * (point_lon, point_lat)
            col, row = int(round(col)), int(round(row))
            
            # 检查点是否在栅格范围内
            if 0 <= row < change_mask.shape[0] and 0 <= col < change_mask.shape[1]:
                is_changed = bool(change_mask[row, col] == 1)
                
                # 检查基准状态
                was_target = False
                if base_mask is not None:
                    was_target = bool(base_mask[row, col] == 1)
                
                return {
                    "is_changed": is_changed,
                    "was_target": was_target,
                    "in_range": True
                }
            
            return {
                "is_changed": False,
                "was_target": False,
                "in_range": False
            }
        except Exception as e:
            logger.error(f"在变化掩膜上查询点 ({point_lon}, {point_lat}) 时出错: {e}")
            return {
                "is_changed": False,
                "was_target": False,
                "in_range": False,
                "error": str(e)
            }

class GlobeLandProcessor:
    """
    GlobeLand30 数据处理器类。
    提供栅格加载、类别筛选及掩膜提取功能。
    """

    def __init__(self, tif_path: str):
        """
        使用指定的 .tif 文件路径初始化处理器。
        
        参数:
            tif_path (str): GlobeLand30 .tif 文件的路径。
        """
        if not os.path.exists(tif_path):
            logger.error(f"未找到栅格文件: {tif_path}")
            raise FileNotFoundError(f"文件不存在: {tif_path}")
        
        self.tif_path = tif_path
        # 预加载元数据，但不加载全部像素以节省内存
        with rasterio.open(self.tif_path) as src:
            self.profile = src.profile
            self.bounds = src.bounds
            self.crs = src.crs
            logger.info(f"成功加载栅格元数据: {tif_path}, 分辨率: {src.res}, 坐标系: {self.crs}")

    def extract_mask(
        self, 
        target_object: str = "耕地",
        bbox: Optional[List[float]] = None, 
        geometry: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, rasterio.profiles.Profile]:
        """
        从栅格中提取指定地物类别的二值掩膜。
        
        参数:
            target_object (str): 目标地物名称，默认为 "耕地"。
            bbox (Optional[List[float]]): 可选的边界框 [min_lon, min_lat, max_lon, max_lat]，坐标系为 EPSG:4326。
                                         如果提供，则仅提取该区域内的掩膜（自动做 CRS 转换）。
            geometry (Optional[Dict[str, Any]]): 可选的行政边界 GeoJSON（EPSG:4326）。如果提供，则在窗口裁剪后按多边形精确裁剪。
                                        
        返回:
            Tuple[np.ndarray, Profile]: 返回二值掩膜数组 (1 为目标地物) 和更新后的栅格 Profile。
        """
        try:
            # 获取地物对应的类别码
            codes = CLASS_MAPPING.get(target_object, (10,))
            if target_object not in CLASS_MAPPING:
                logger.warning(f"未定义地物类型 '{target_object}'，默认使用耕地类别码 (10)。")

            with rasterio.open(self.tif_path) as src:
                if geometry and not bbox:
                    try:
                        from shapely.geometry import shape
                        bbox = list(shape(geometry).bounds)
                    except Exception:
                        bbox = None

                if bbox:
                    # 使用窗口化读取 (Windowed Read) 以优化内存
                    bbox_src = transform_bounds("EPSG:4326", src.crs, *bbox, densify_pts=21)
                    window = from_bounds(*bbox_src, transform=src.transform)
                    try:
                        window = window.intersection(Window(0, 0, src.width, src.height))
                    except Exception:
                        raise ValueError("裁剪窗口与栅格无交集，请检查边界范围与分幅匹配。")
                    data = src.read(1, window=window)
                    transform = src.window_transform(window)
                else:
                    data = src.read(1)
                    transform = src.transform

                # 提取目标地物掩膜
                mask = np.isin(data, codes)

                if geometry:
                    geom_in_src = transform_geom("EPSG:4326", src.crs, geometry, precision=6)
                    inside = geometry_mask(
                        [geom_in_src],
                        out_shape=(mask.shape[0], mask.shape[1]),
                        transform=transform,
                        invert=True,
                        all_touched=False,
                    )
                    mask = mask & inside
                
                # 更新 Profile 以匹配输出数据
                out_profile = src.profile.copy()
                out_profile.update({
                    "driver": "GTiff",
                    "height": mask.shape[0],
                    "width": mask.shape[1],
                    "transform": transform,
                    "dtype": "uint8",
                    "count": 1,
                    "nodata": 0
                })
                
                target_count = np.sum(mask)
                logger.info(f"掩膜提取完成。目标 [{target_object}] 像素总数: {target_count}")
                
                return mask.astype(np.uint8), out_profile

        except Exception as e:
            logger.error(f"提取 [{target_object}] 掩膜时出错: {e}")
            raise

    def extract_farmland_mask(self, *args, **kwargs):
        """兼容旧版方法名。"""
        return self.extract_mask(*args, **kwargs)

    def save_mask(self, mask: np.ndarray, profile: rasterio.profiles.Profile, output_path: str):
        """
        将提取的掩膜保存为新的 GeoTIFF 文件。
        
        参数:
            mask (np.ndarray): 二值掩膜数组。
            profile (Profile): 栅格配置文件。
            output_path (str): 保存路径。
        """
        try:
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(mask, 1)
            logger.info(f"掩膜已成功保存至: {output_path}")
        except Exception as e:
            logger.error(f"保存掩膜文件失败: {e}")
            raise

