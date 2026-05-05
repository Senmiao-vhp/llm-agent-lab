"""
GIS 数据路径与常量 — 对齐原 app2 `core/config`，统一使用 APP3_* 与 app3 项目根下 `data/`。
"""

from __future__ import annotations

import os
from pathlib import Path


def _project_root() -> Path:
    """llm-agent-lab/app3（含 pyproject.toml）。"""
    return Path(__file__).resolve().parent.parent.parent


def _default_data_dir() -> str:
    return str(_project_root() / "data")


DATA_DIR = os.getenv("APP3_DATA_DIR") or _default_data_dir()

_DEFAULT_GLOBELAND = os.path.join(DATA_DIR, "raw", "GlobeLand30.2020", "GlobeLand30.2020")
GLOBELAND30_DIR = os.getenv("APP3_GLOBELAND30_DIR") or _DEFAULT_GLOBELAND
RAW_DATA_DIR = GLOBELAND30_DIR

PROCESSED_DATA_DIR = os.getenv("APP3_PROCESSED_DATA_DIR") or os.path.join(DATA_DIR, "processed")
RAW_ADMIN_BOUNDARY_DIR = os.getenv("APP3_RAW_ADMIN_BOUNDARY_DIR") or os.path.join(
    DATA_DIR, "raw", "admin_boundaries"
)
PROCESSED_ADMIN_BOUNDARY_DIR = os.getenv("APP3_PROCESSED_ADMIN_BOUNDARY_DIR") or os.path.join(
    PROCESSED_DATA_DIR, "admin_boundaries"
)
TASK_STORE_DIR = os.getenv("APP3_TASK_STORE_DIR") or os.path.join(DATA_DIR, "tasks")

CRS_DEFAULT = "EPSG:4326"
FARMLAND_CLASS_CODE = 10
FARMLAND_CLASS_CODES = (10, 11, 12)


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return default
