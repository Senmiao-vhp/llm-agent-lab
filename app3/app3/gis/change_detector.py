"""
耕地变化检测模块。
负责比对多时相遥感影像，在耕地掩膜范围内识别疑似“非农化”区域。
"""

import os
import logging
import numpy as np
import rasterio
from typing import Tuple, Dict, Any, Optional

# 设置本模块的日志记录器
logger = logging.getLogger(__name__)

class ChangeDetector:
    """
    变化检测器类。
    实现基于植被指数（NDVI）差异或影像代数的变化检测算法。
    """

    @staticmethod
    def calculate_ndvi(red_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
        """
        计算归一化植被指数 (NDVI)。
        
        参数:
            red_band (np.ndarray): Red 波段数组。
            nir_band (np.ndarray): NIR（近红外）波段数组。
            
        返回:
            np.ndarray: NDVI 数组，范围 [-1, 1]。
            
        数学逻辑:
            NDVI = (NIR - Red) / (NIR + Red)
        """
        # 使用 numpy 的高效方法计算，同时处理分母为 0 的情况
        red = red_band.astype(np.float32)
        nir = nir_band.astype(np.float32)
        
        denominator = nir + red
        numerator = nir - red
        
        # 仅对分母不为 0 的像素进行除法，其余设为 0
        return np.divide(numerator, denominator, out=np.zeros_like(denominator), where=denominator != 0)

    def detect_farmland_loss(
        self, 
        base_mask: np.ndarray, 
        t1_image: Dict[str, np.ndarray], 
        t2_image: Dict[str, np.ndarray],
        threshold: float = -0.2,
        apply_denoise: bool = True
    ) -> np.ndarray:
        """
        识别耕地流失（非农化）区域。
        
        参数:
            base_mask (np.ndarray): 耕地基准掩膜（GlobeLand30 提取，1 为耕地）。
            t1_image (Dict): 基准期影像波段数据（需包含 'red' 和 'nir'）。
            t2_image (Dict): 监测期影像波段数据（需包含 'red' 和 'nir'）。
            threshold (float): NDVI 变化阈值。负值表示植被减少。
            apply_denoise (bool): 是否应用开闭运算进行降噪。
            
        返回:
            np.ndarray: 疑似流失区域的二值掩膜（1 为流失）。
        """
        logger.info(f"开始执行变化检测算法 (阈值: {threshold})...")
        
        # 1. 计算两期 NDVI
        ndvi_t1 = self.calculate_ndvi(t1_image['red'], t1_image['nir'])
        ndvi_t2 = self.calculate_ndvi(t2_image['red'], t2_image['nir'])
        
        # 2. 计算差异
        ndvi_diff = ndvi_t2 - ndvi_t1
        
        # 3. 识别耕地范围内植被显著减少的区域
        loss_mask = (base_mask == 1) & (ndvi_diff < threshold)
        loss_mask = loss_mask.astype(np.uint8)

        # 4. 可选：形态学降噪（移除孤立的小像素点）
        if apply_denoise:
            try:
                import cv2
                kernel = np.ones((3, 3), np.uint8)
                # 开运算：先腐蚀后膨胀，移除噪声
                loss_mask = cv2.morphologyEx(loss_mask, cv2.MORPH_OPEN, kernel)
                logger.info("已应用形态学降噪 (MORPH_OPEN)。")
            except ImportError:
                logger.warning("未安装 opencv-python，跳过降噪步骤。")
        
        loss_count = np.sum(loss_mask)
        logger.info(f"变化检测完成。识别到疑似流失像素点: {loss_count}")
        
        return loss_mask

    def save_result(self, result_mask: np.ndarray, profile: rasterio.profiles.Profile, output_path: str):
        """
        保存变化检测结果为 GeoTIFF。
        """
        try:
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(result_mask, 1)
            logger.info(f"变化检测结果已保存至: {output_path}")
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            raise

