"""
GlobeLand30 数据解压模块。
提供用于管理、列出和解压 GlobeLand30 土地覆盖压缩包的工具。
"""

import os
import zipfile
import logging
import threading
import rasterio
from typing import Dict, List, Optional
from app3.gis.config_paths import GLOBELAND30_DIR, PROCESSED_DATA_DIR

# 设置本模块的日志记录器
logger = logging.getLogger(__name__)

class GlobeLandUnpacker:
    """
    用于处理 GlobeLand30 分幅数据解压的工具类。
    帮助根据地理感兴趣区域 (AOI) 识别并解压特定的 .zip 文件。
    """
    
    def __init__(self, raw_dir: str = GLOBELAND30_DIR, output_dir: str = PROCESSED_DATA_DIR):
        """
        使用原始数据目录和处理后数据目录初始化解压器。
        
        参数:
            raw_dir (str): 包含 GlobeLand30 压缩包的目录路径。
            output_dir (str): 文件解压后的目标路径。
        """
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # tile zip name -> extracted lc030 tif path (process-local cache)
        self._tile_cache: Dict[str, str] = {}
        self._tile_cache_lock = threading.Lock()

    def list_available_zips(self) -> List[str]:
        """
        扫描原始数据目录，获取所有可用的 GlobeLand30 .zip 文件。
        
        返回:
            List[str]: 压缩包文件名列表。
        """
        if not os.path.exists(self.raw_dir):
            logger.warning(f"原始数据目录 {self.raw_dir} 不存在。")
            return []
        return [f for f in os.listdir(self.raw_dir) if f.endswith('.zip')]

    def unpack_tile(self, tile_name: str) -> Optional[str]:
        """
        解压特定的 GlobeLand30 分幅，并定位其中的土地覆盖 GeoTIFF 主文件。
        
        参数:
            tile_name (str): 待解压的压缩包名称（例如：'N42_50_2020LC030.zip'）。
            
        Returns:
            Optional[str]: 解压后的 .tif 文件绝对路径，如果解压失败则返回 None。
        """
        # 快速路径：若缓存命中且文件仍存在，直接返回
        with self._tile_cache_lock:
            cached = self._tile_cache.get(tile_name)
        if cached and os.path.exists(cached):
            return cached

        zip_path = os.path.join(self.raw_dir, tile_name)
        if not os.path.exists(zip_path):
            logger.error(f"未找到 GlobeLand30 压缩包: {zip_path}")
            return None
            
        # 以分幅名命名目标目录（去掉 .zip 后缀）
        target_dir = os.path.join(self.output_dir, tile_name.replace('.zip', ''))
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        try:
            logger.info(f"正在将 {tile_name} 解压至 {target_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
                
            # 定位内部的 .tif 主文件
            tif_path = None
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.lower().endswith('.tif') and 'lc030' in file.lower():
                        tif_path = os.path.abspath(os.path.join(root, file))
                        break
                if tif_path: break
            
            if not tif_path:
                logger.warning(f"在 {target_dir} 中未找到匹配 'lc030' 的 .tif 文件。")
                return None

            # 验证 TIFF 文件是否损坏
            try:
                with rasterio.open(tif_path) as src:
                    _ = src.profile
                logger.info(f"找到并验证了土地覆盖 TIF 文件: {tif_path}")
                with self._tile_cache_lock:
                    self._tile_cache[tile_name] = tif_path
                return tif_path
            except Exception as e:
                logger.error(f"解压后的 TIF 文件损坏或无法打开: {tif_path}, 错误: {e}")
                return None

        except zipfile.BadZipFile as e:
            logger.error(f"解压 {tile_name} 失败 (BadZipFile): {e}")
            return None
        except Exception as e:
            logger.error(f"处理 {tile_name} 时发生未知错误: {e}")
            return None

    def cleanup_temp_files(self):
        """
        清理解压缩后的临时目录。
        仅删除 self.output_dir 下的子目录，不影响原始压缩包。
        """
        import shutil
        if not os.path.exists(self.output_dir):
            return
            
        logger.info(f"正在清理临时目录: {self.output_dir}")
        for item in os.listdir(self.output_dir):
            item_path = os.path.join(self.output_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    logger.debug(f"已删除目录: {item_path}")
                elif os.path.isfile(item_path) and not item.startswith('.'):
                    # 也可以选择删除生成的中间 TIFF 文件
                    os.remove(item_path)
                    logger.debug(f"已删除文件: {item_path}")
            except Exception as e:
                logger.warning(f"无法删除 {item_path}: {e}")
        logger.info("临时文件清理完成。")

    @staticmethod
    def get_tile_name_from_coord(lat: float, lon: float) -> str:
        """
        根据 WGS84 坐标匹配 GlobeLand30 2020版的分幅名称。
        
        分幅规则：
        1. 经度方向：按 UTM 6度带分幅。Zone = int((lon + 180) / 6) + 1。
        2. 纬度方向：按 5度 间隔分幅，文件名使用该区间【下界】。
           例如：北京 (39.9N) 属于 35-40 度区间，标识为 35。
        
        格式：N[Zone]_[LatUpper]_2020LC030.zip
        """
        import math
        # 1. 计算 UTM 带号 (1-60)
        zone = int((lon + 180) / 6) + 1
        
        # 2. 计算纬度区间下界 (5的倍数)
        lat_lower = int(math.floor(lat / 5.0) * 5)
        
        # 格式化带号为两位数字 (如 50, 09)
        zone_str = f"{zone:02d}"
        lat_str = f"{lat_lower:02d}"
        
        return f"N{zone_str}_{lat_str}_2020LC030.zip"

    @staticmethod
    def get_tile_names_from_bbox(bbox_wgs84: List[float]) -> List[str]:
        """
        根据 WGS84 BBox 计算可能覆盖该区域的 GlobeLand30 分幅列表。

        参数:
            bbox_wgs84 (List[float]): [min_lon, min_lat, max_lon, max_lat]
        """
        import math

        min_lon, min_lat, max_lon, max_lat = bbox_wgs84
        min_zone = int((min_lon + 180) / 6) + 1
        max_zone = int((max_lon + 180) / 6) + 1
        zones = list(range(min_zone, max_zone + 1))

        min_lower = int(math.floor(min_lat / 5.0) * 5)
        max_lower = int(math.floor(max_lat / 5.0) * 5)
        lat_lowers = list(range(min_lower, max_lower + 1, 5))

        tiles: List[str] = []
        for z in zones:
            for lat_lower in lat_lowers:
                tiles.append(f"N{z:02d}_{lat_lower:02d}_2020LC030.zip")
        return tiles

