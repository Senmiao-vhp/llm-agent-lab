"""运行时配置（基于环境变量；遵循常见的 OpenAI 兼容模式）。"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_base_url: str | None
    default_chat_model: str

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            default_chat_model=_env("MOONSHOT_MODEL") or _env("OPENAI_MODEL") or "gpt-4o-mini",
        )
