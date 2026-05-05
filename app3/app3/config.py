"""运行时配置（基于环境变量；遵循常见的 OpenAI 兼容模式）。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _app3_project_root() -> Path:
    """含 pyproject.toml 的 app3 目录（…/llm-agent-lab/app3）。"""
    return Path(__file__).resolve().parent.parent


def _load_env_file(path: str) -> None:
    """按 KEY=VALUE 合并进进程环境；仅当变量未设置或为空时写入。"""
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                if not key:
                    continue
                val = val.strip().strip('"').strip("'")
                current = os.getenv(key)
                if current is None or not str(current).strip():
                    os.environ[key] = val
    except OSError:
        return


def apply_optional_env_file() -> None:
    """
    加载 env 文件（可多文件顺序合并，同名变量：**先出现的占位，后不覆盖非空**）。

    1. 若 ``APP3_SKIP_ENV_FILE=1``：跳过（供单测等场景）。
    2. 若设置 ``APP3_ENV_FILE`` 且文件存在：先加载（可与下面叠加）。
    3. 若 ``<app3 项目根>/.env`` 存在：再加载；用于补全 Neo4j / EMBEDDING 等（典型场景： shells 里仍指向其它项目的 APP3_ENV_FILE 时，不影响读取 app3/.env）。

    模板见 ``app3/.env.example``。
    """
    skip = (os.getenv("APP3_SKIP_ENV_FILE") or "").strip().lower()
    if skip in ("1", "true", "yes", "on"):
        return

    paths: list[Path] = []
    explicit = (os.getenv("APP3_ENV_FILE") or "").strip()
    if explicit:
        ep = Path(explicit)
        if ep.is_file():
            paths.append(ep)

    default_dotenv = _app3_project_root() / ".env"
    if default_dotenv.is_file():
        paths.append(default_dotenv)

    seen_resolved: set[Path] = set()
    for p in paths:
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp in seen_resolved:
            continue
        seen_resolved.add(rp)
        _load_env_file(str(p))


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


def _env_bool(name: str, *, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_base_url: str | None
    default_chat_model: str
    neo4j_uri: str | None
    neo4j_user: str | None
    neo4j_password: str | None
    neo4j_database: str | None
    graph_rag_enabled: bool = False
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    neo4j_chunk_vector_index: str = "chunk_embedding_index"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None

    @staticmethod
    def from_env() -> "Settings":
        apply_optional_env_file()
        return Settings(
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            default_chat_model=_env("MOONSHOT_MODEL") or _env("OPENAI_MODEL") or "gpt-4o-mini",
            neo4j_uri=_env("NEO4J_URI"),
            neo4j_user=_env("NEO4J_USER"),
            neo4j_password=_env("NEO4J_PASSWORD"),
            neo4j_database=_env("NEO4J_DATABASE"),
            graph_rag_enabled=_env_bool("GRAPH_RAG_ENABLED", default=False),
            embedding_model=_env("EMBEDDING_MODEL") or "text-embedding-3-small",
            embedding_dimensions=_env_int("EMBEDDING_DIMENSIONS", 1536),
            neo4j_chunk_vector_index=_env("NEO4J_CHUNK_VECTOR_INDEX") or "chunk_embedding_index",
            embedding_api_key=_env("EMBEDDING_API_KEY"),
            embedding_base_url=_env("EMBEDDING_BASE_URL"),
        )
