"""规范化错误载荷 — 便于日志、状态序列化与分类。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ErrorEnvelope:
    kind: Literal["fatal", "recoverable"]
    subtype: str
    message: str
    http_status: int | None = None
    source: str = "unknown"
    cause: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ErrorEnvelope":
        return ErrorEnvelope(
            kind=d["kind"],
            subtype=str(d["subtype"]),
            message=str(d["message"]),
            http_status=d.get("http_status"),
            source=str(d.get("source") or "unknown"),
            cause=d.get("cause"),
            extra=dict(d.get("extra") or {}),
        )
