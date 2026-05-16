"""规划器参数：默认表、深度合并、``APP3_PLANNER_PARAMS`` / 默认 JSON 加载。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app3.config import _app3_project_root

logger = logging.getLogger(__name__)

DEFAULT_PLANNER_PARAMS: dict[str, Any] = {
    "ndvi_threshold": 0.15,
    "search_satellite": {"max_cloud_cover": 20.0},
    "change_detection": {"export_geojson": True, "max_features": 5000},
    "trend": {
        "max_cloud_cover": 40.0,
        "scale_m": 200,
        "download_timeout": 360,
        "date_half_width_days": 40,
        "per_year_retries": 3,
        "retry_sleep_s": [4.0, 8.0],
    },
    "parallel": {"enabled": True, "max_workers": 4},
}


def deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a or {})
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _try_load_json_file(path: str) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        if isinstance(user, dict):
            return user
        logger.warning("planner params file is not a JSON object: %s", path)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        logger.warning("invalid planner params JSON %s: %s", path, e)
    except OSError as e:
        logger.warning("cannot read planner params %s: %s", path, e)
    return None


def load_planner_params() -> tuple[dict[str, Any], str]:
    """
    返回 ``(params, source)``。
    ``source`` ∈ ``env`` | ``default_file`` | ``defaults_only``。
    """
    base = dict(DEFAULT_PLANNER_PARAMS)
    env_path = (os.getenv("APP3_PLANNER_PARAMS") or "").strip()
    if env_path and os.path.isfile(env_path):
        user = _try_load_json_file(env_path)
        if user is not None:
            return deep_merge(base, user), "env"
        logger.warning("APP3_PLANNER_PARAMS set but file missing or invalid: %s", env_path)

    default_path = str(_app3_project_root() / "config" / "planner_params.json")
    if os.path.isfile(default_path):
        user = _try_load_json_file(default_path)
        if user is not None:
            return deep_merge(base, user), "default_file"

    return base, "defaults_only"
