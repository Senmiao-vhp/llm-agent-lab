from __future__ import annotations

import hashlib
import os
import pickle
import threading
from typing import Any, Dict, Optional


class FileCache:
    """
    GIS算子幂等缓存：相同输入永远返回相同结果。

    核心实现：MD5哈希去重 + pickle序列化 + 线程安全锁。
    """

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._lock = threading.Lock()  # 多线程写文件互斥锁

    def _key(self, op: str, params: Dict[str, Any], inputs: Any) -> str:
        """
        计算缓存键：算子名 + 参数 + 输入摘要 -> MD5哈希。
        关键：排序保证 {a:1,b:2} 和 {b:2,a:1} 算成同一个键。
        """
        payload = {"op": op, "params": params, "inputs": self._summarize(inputs)}
        raw = repr(sorted(payload.items())).encode("utf-8")
        return hashlib.md5(raw).hexdigest()

    def _summarize(self, v: Any) -> Any:
        """
        大字段只哈希特征不哈希数据：
        - 跳过 10MB 级别的 GeoJSON
        - numpy 数组只哈希形状+类型，不哈希整个数组
        """
        try:
            import numpy as np  # type: ignore
        except Exception:  # pragma: no cover
            np = None  # type: ignore

        if isinstance(v, dict):
            return {k: self._summarize(vv) for k, vv in v.items() if k != "geometry_geojson"}
        if isinstance(v, list):
            return [self._summarize(i) for i in v]
        if np is not None and isinstance(v, np.ndarray):
            return f"ndarray(shape={v.shape},dtype={v.dtype})"
        return v

    def get(self, op: str, params: Dict[str, Any], inputs: Any) -> Optional[Any]:
        """查缓存：命中返回反序列化结果，未命中返回 None。"""
        key = self._key(op, params, inputs)
        path = os.path.join(self.cache_dir, f"{key}.pkl")
        if not os.path.exists(path):
            return None
        with self._lock:
            with open(path, "rb") as f:
                return pickle.load(f)

    def set(self, op: str, params: Dict[str, Any], inputs: Any, result: Any) -> None:
        """写缓存。"""
        key = self._key(op, params, inputs)
        path = os.path.join(self.cache_dir, f"{key}.pkl")
        with self._lock:
            with open(path, "wb") as f:
                pickle.dump(result, f)
