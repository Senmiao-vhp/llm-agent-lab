"""异常 → ErrorEnvelope（集中映射，避免节点散落魔法字符串）。"""

from __future__ import annotations

import errno

from app3.errors.envelope import ErrorEnvelope
from app3.errors.taxonomy import FatalSubtype, RecoverableSubtype
from app3.llm.errors import LLMConfigError


def map_http_status(status: int | None, *, message: str, source: str) -> ErrorEnvelope:
    if status is None:
        return ErrorEnvelope(
            kind="recoverable",
            subtype=RecoverableSubtype.UNKNOWN.value,
            message=message,
            source=source,
        )
    if status == 401 or status == 403:
        return ErrorEnvelope(
            kind="fatal",
            subtype=FatalSubtype.AUTH.value,
            message=message,
            http_status=status,
            source=source,
        )
    if status == 429:
        return ErrorEnvelope(
            kind="recoverable",
            subtype=RecoverableSubtype.RATE_LIMIT.value,
            message=message,
            http_status=status,
            source=source,
        )
    if status >= 500:
        return ErrorEnvelope(
            kind="recoverable",
            subtype=RecoverableSubtype.UPSTREAM_5XX.value,
            message=message,
            http_status=status,
            source=source,
        )
    if status >= 400:
        return ErrorEnvelope(
            kind="fatal",
            subtype=FatalSubtype.BAD_REQUEST.value,
            message=message,
            http_status=status,
            source=source,
        )
    return ErrorEnvelope(
        kind="recoverable",
        subtype=RecoverableSubtype.UNKNOWN.value,
        message=message,
        http_status=status,
        source=source,
    )


def classify_exception(exc: BaseException, *, source: str = "unknown") -> ErrorEnvelope:
    """将常见 SDK/网络异常映射为 fatal/recoverable + subtype。"""
    msg = str(exc).strip() or repr(exc)
    cause = type(exc).__name__

# 第一层：特定异常类型识别
    # 1. LLM配置错误（致命）
    if isinstance(exc, LLMConfigError):
        return ErrorEnvelope(
            kind="fatal",
            subtype=FatalSubtype.CONFIG.value,
            message=msg,
            source=source,
            cause=cause,
        )

    # Neo4j / Bolt（可恢复：连接、会话、瞬时错误）
    try:
        from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

        if isinstance(exc, (ServiceUnavailable, SessionExpired)):
            return ErrorEnvelope(
                kind="recoverable",
                subtype=RecoverableSubtype.NETWORK.value,
                message=msg,
                source=source,
                cause=cause,
            )
        if isinstance(exc, TransientError):
            return ErrorEnvelope(
                kind="recoverable",
                subtype=RecoverableSubtype.TIMEOUT.value,
                message=msg,
                source=source,
                cause=cause,
            )
    except ImportError:
        pass

    # 2. 系统级网络错误（可恢复）
    if isinstance(exc, OSError) and exc.errno is not None:
        if exc.errno in {
            errno.ETIMEDOUT,
            errno.ECONNRESET,
            errno.ECONNREFUSED,
            errno.ECONNABORTED,
            errno.EHOSTUNREACH,
            errno.ENETUNREACH,
        }:
            return ErrorEnvelope(
                kind="recoverable",
                subtype=RecoverableSubtype.NETWORK.value,
                message=msg,
                source=source,
                cause=cause,
            )

# 第二层：错误消息模式匹配
    # 基于错误消息内容进行分类
    low = msg.lower()
    if "timeout" in low or "timed out" in low:
        return ErrorEnvelope(
            kind="recoverable",
            subtype=RecoverableSubtype.TIMEOUT.value,
            message=msg,
            source=source,
            cause=cause,
        )
    if "rate limit" in low or "429" in low or "too many requests" in low:
        return ErrorEnvelope(
            kind="recoverable",
            subtype=RecoverableSubtype.RATE_LIMIT.value,
            message=msg,
            source=source,
            cause=cause,
        )
    if "connection" in low or "network" in low or "temporarily unavailable" in low:
        return ErrorEnvelope(
            kind="recoverable",
            subtype=RecoverableSubtype.NETWORK.value,
            message=msg,
            source=source,
            cause=cause,
        )

# 第三层：HTTP状态码检查
    # 检查异常对象是否有状态码属性
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int):
        return map_http_status(status, message=msg, source=source)

# 第四层：特定SDK异常处理
    # OpenAI SDK异常
    try:
        from openai import APIStatusError  # type: ignore[attr-defined]

        if isinstance(exc, APIStatusError):
            st = getattr(exc, "status_code", None)
            if isinstance(st, int):
                return map_http_status(st, message=msg, source=source)
    except ImportError:
        pass
    
    # HTTPx异常
    try:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError):
            st = exc.response.status_code if exc.response is not None else None
            return map_http_status(st, message=msg, source=source)
    except ImportError:
        pass

# 第五层：默认分类
    # 无法识别的异常默认为可恢复的未知错误
    return ErrorEnvelope(
        kind="recoverable",
        subtype=RecoverableSubtype.UNKNOWN.value,
        message=msg,
        source=source,
        cause=cause,
    )
