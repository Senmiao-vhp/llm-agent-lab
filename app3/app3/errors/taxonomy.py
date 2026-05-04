"""错误子类型枚举 — 用于策略表与指标。"""

from __future__ import annotations

from enum import StrEnum


class FatalSubtype(StrEnum):
    CONFIG = "fatal_config"
    AUTH = "fatal_auth"
    QUOTA = "fatal_quota"
    BAD_REQUEST = "fatal_bad_request"
    POLICY = "fatal_policy"
    RETRIES_EXHAUSTED = "fatal_retries_exhausted"
    UNKNOWN = "fatal_unknown"


class RecoverableSubtype(StrEnum):
    RATE_LIMIT = "recv_rate_limit"
    TIMEOUT = "recv_timeout"
    NETWORK = "recv_network"
    UPSTREAM_5XX = "recv_upstream_5xx"
    TOOL = "recv_tool"
    UNKNOWN = "recv_unknown"
