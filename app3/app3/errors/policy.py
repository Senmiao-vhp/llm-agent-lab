"""按 recoverable 子类型的重试上限与指数退避。"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

from app3.errors.taxonomy import RecoverableSubtype

_GLOBAL_DEFAULT_RETRIES = 3


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


# 各类 recoverable 的专用最大恢复次数（每次进入 handle_error 计 1）
MAX_RETRIES_BY_RECOVERABLE: dict[str, int] = {
    RecoverableSubtype.RATE_LIMIT.value: 8,
    RecoverableSubtype.TIMEOUT.value: 5,
    RecoverableSubtype.NETWORK.value: 6,
    RecoverableSubtype.UPSTREAM_5XX.value: 5,
    RecoverableSubtype.TOOL.value: 4,
    RecoverableSubtype.UNKNOWN.value: 3,
}


@dataclass(frozen=True)
class BackoffProfile:
    base_seconds: float
    cap_seconds: float


BACKOFF_PROFILE_BY_SUBTYPE: dict[str, BackoffProfile] = {
    RecoverableSubtype.RATE_LIMIT.value: BackoffProfile(base_seconds=2.0, cap_seconds=120.0),
    RecoverableSubtype.TIMEOUT.value: BackoffProfile(base_seconds=1.0, cap_seconds=60.0),
    RecoverableSubtype.NETWORK.value: BackoffProfile(base_seconds=1.0, cap_seconds=60.0),
    RecoverableSubtype.UPSTREAM_5XX.value: BackoffProfile(base_seconds=1.5, cap_seconds=90.0),
    RecoverableSubtype.TOOL.value: BackoffProfile(base_seconds=1.0, cap_seconds=60.0),
    RecoverableSubtype.UNKNOWN.value: BackoffProfile(base_seconds=1.0, cap_seconds=30.0),
}


def get_max_retries(subtype: str, *, fallback: int | None = None) -> int:
    """未知 subtype 时使用 fallback，否则使用全局默认。"""
    if subtype in MAX_RETRIES_BY_RECOVERABLE:
        return MAX_RETRIES_BY_RECOVERABLE[subtype]
    return fallback if fallback is not None else _GLOBAL_DEFAULT_RETRIES


def compute_backoff_seconds(
    subtype: str,
    attempt_index: int,
    *,
    jitter_ratio: float | None = None,
    rng: random.Random | None = None,
) -> float:
    """
    指数退避：base * 2**attempt_index + 抖动；再由环境与 subtype cap 限制。
    attempt_index 从 0 开始（首次恢复等待）。
    """
    jitter_ratio = jitter_ratio if jitter_ratio is not None else _env_float("APP3_BACKOFF_JITTER_RATIO", 0.12)
    profile = BACKOFF_PROFILE_BY_SUBTYPE.get(subtype, BackoffProfile(base_seconds=1.0, cap_seconds=30.0))
    raw = profile.base_seconds * (2.0**max(0, attempt_index))
    raw = min(raw, profile.cap_seconds)
    env_cap = _env_float("APP3_BACKOFF_MAX_SECONDS", 120.0)
    raw = min(raw, env_cap)
    r = rng or random.Random()
    jitter = r.uniform(0.0, jitter_ratio * raw) if jitter_ratio > 0 else 0.0
    return float(raw + jitter)
