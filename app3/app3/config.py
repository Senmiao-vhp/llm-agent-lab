"""运行时配置（基于环境变量；遵循常见的 OpenAI 兼容模式）。

本模块是唯一允许读取进程环境（含 .env 合并结果）的位置；业务代码通过 ``Settings`` 注入。
未设置或空串的变量使用下方 ``Settings`` 字段默认值；一旦在环境中写出非空值，则须为合法类型，
否则 ``Settings.from_env()`` 抛出 ``ValueError``（布尔仅 ``true`` / ``false``，大小写不敏感）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path


def _app3_project_root() -> Path:
    """含 pyproject.toml 的 app3 目录（…/llm-agent-lab/app3）。"""
    return Path(__file__).resolve().parent.parent


def apply_optional_env_file() -> None:
    """
    若 ``<app3 项目根>/.env`` 存在则读取：按 KEY=VALUE 合并进进程环境，
    仅当变量未设置或为空时写入（不覆盖已有非空环境变量）。

    模板见 ``app3/.env.example``。
    """
    dotenv = _app3_project_root() / ".env"
    if not dotenv.is_file():
        return
    try:
        with open(dotenv, encoding="utf-8") as f:
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


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


def _strict_bool(name: str, *, absent_default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return absent_default
    s = str(raw).strip().lower()
    if s == "true":
        return True
    if s == "false":
        return False
    raise ValueError(f"环境变量 {name} 必须为 true 或 false (不区分大小写)，当前值: {raw!r}")


def _strict_int(name: str, *, absent_default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return absent_default
    try:
        return int(str(raw).strip(), 10)
    except ValueError as e:
        raise ValueError(f"环境变量 {name} 必须为整数，当前值: {raw!r}") from e


def _strict_float(name: str, *, absent_default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return absent_default
    try:
        return float(str(raw).strip())
    except ValueError as e:
        raise ValueError(f"环境变量 {name} 必须为浮点数，当前值: {raw!r}") from e


def _strict_optional_positive_int(name: str) -> int | None:
    """未设置或空串为 None；已设置则须为大于 0 的整数。"""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        n = int(str(raw).strip(), 10)
    except ValueError as e:
        raise ValueError(f"环境变量 {name} 必须为大于 0 的整数或未设置，当前值: {raw!r}") from e
    if n <= 0:
        raise ValueError(f"环境变量 {name} 必须为大于 0 的整数，当前值: {raw!r}")
    return n


def _default_data_dir_str() -> str:
    return str(_app3_project_root() / "data")


def _path_bundle_from_data_dir(data_dir: str) -> tuple[str, str, str, str, str, str]:
    root = Path(data_dir)
    globeland30 = str(root / "raw" / "GlobeLand30.2020" / "GlobeLand30.2020")
    processed = str(root / "processed")
    raw_admin = str(root / "raw" / "admin_boundaries")
    processed_admin = str(Path(processed) / "admin_boundaries")
    tasks = str(root / "tasks")
    return (str(root), globeland30, processed, raw_admin, processed_admin, tasks)


_d0, _g0, _p0, _ra0, _pa0, _t0 = _path_bundle_from_data_dir(_default_data_dir_str())


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    default_chat_model: str = "gpt-4o-mini"
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str | None = None
    graph_rag_enabled: bool = False
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    neo4j_chunk_vector_index: str = "chunk_embedding_index"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    gee_project_id: str | None = None
    gis_cache_dir: str | None = None
    gis_use_cache: bool = True
    explainer_llm: bool = True
    plan_use_llm: bool = False
    backoff_max_seconds: float = 120.0
    backoff_jitter_ratio: float = 0.12
    gis_nominatim_enabled: bool = True
    nominatim_user_agent: str | None = None
    geo_fallback_nominatim: bool = False
    executor_parallel: bool = True
    executor_parallel_workers: int | None = None
    data_dir: str = _d0
    globeland30_dir: str = _g0
    processed_data_dir: str = _p0
    raw_admin_boundary_dir: str = _ra0
    processed_admin_boundary_dir: str = _pa0
    task_store_dir: str = _t0
    # data/refs/district/district.csv 存在时 from_env 默认填入；APP3_DISTRICT_NORMALIZE=false 关闭
    district_csv_path: str | None = None

    @staticmethod
    def from_env() -> "Settings":
        apply_optional_env_file()
        data_dir = (_env("APP3_DATA_DIR") or "").strip() or _default_data_dir_str()
        _pb = _path_bundle_from_data_dir(data_dir)
        globeland30_dir = (_env("APP3_GLOBELAND30_DIR") or "").strip() or _pb[1]
        processed_data_dir = (_env("APP3_PROCESSED_DATA_DIR") or "").strip() or _pb[2]
        raw_admin_boundary_dir = (_env("APP3_RAW_ADMIN_BOUNDARY_DIR") or "").strip() or _pb[3]
        processed_admin_boundary_dir = (_env("APP3_PROCESSED_ADMIN_BOUNDARY_DIR") or "").strip() or _pb[4]
        task_store_dir = (_env("APP3_TASK_STORE_DIR") or "").strip() or _pb[5]

        graph_rag_enabled = _strict_bool("GRAPH_RAG_ENABLED", absent_default=False)
        embedding_dimensions = _strict_int("EMBEDDING_DIMENSIONS", absent_default=1536)
        gis_use_cache = _strict_bool("APP3_GIS_USE_CACHE", absent_default=True)
        explainer_llm = _strict_bool("APP3_EXPLAINER_LLM", absent_default=False)
        plan_use_llm = _strict_bool("APP3_PLAN_USE_LLM", absent_default=True)
        backoff_max_seconds = _strict_float("APP3_BACKOFF_MAX_SECONDS", absent_default=120.0)
        backoff_jitter_ratio = _strict_float("APP3_BACKOFF_JITTER_RATIO", absent_default=0.12)
        gis_nominatim_enabled = _strict_bool("APP3_GIS_NOMINATIM", absent_default=True)
        geo_fallback_nominatim = _strict_bool("APP3_GEO_FALLBACK_NOMINATIM", absent_default=False)
        executor_parallel = _strict_bool("APP3_EXECUTOR_PARALLEL", absent_default=True)
        executor_parallel_workers = _strict_optional_positive_int("APP3_EXECUTOR_PARALLEL_WORKERS")

        district_normalize = _strict_bool("APP3_DISTRICT_NORMALIZE", absent_default=True)
        _district_default = _app3_project_root() / "data" / "refs" / "district" / "district.csv"
        _district_explicit = (_env("APP3_DISTRICT_CSV") or "").strip()
        if not district_normalize:
            district_csv_path: str | None = None
        elif _district_explicit:
            district_csv_path = _district_explicit
        elif _district_default.is_file():
            district_csv_path = str(_district_default)
        else:
            district_csv_path = None

        return Settings(
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            default_chat_model=_env("MOONSHOT_MODEL") or _env("OPENAI_MODEL") or "gpt-4o-mini",
            neo4j_uri=_env("NEO4J_URI"),
            neo4j_user=_env("NEO4J_USER"),
            neo4j_password=_env("NEO4J_PASSWORD"),
            neo4j_database=_env("NEO4J_DATABASE"),
            graph_rag_enabled=graph_rag_enabled,
            embedding_model=_env("EMBEDDING_MODEL") or "text-embedding-3-small",
            embedding_dimensions=embedding_dimensions,
            neo4j_chunk_vector_index=_env("NEO4J_CHUNK_VECTOR_INDEX") or "chunk_embedding_index",
            embedding_api_key=_env("EMBEDDING_API_KEY"),
            embedding_base_url=_env("EMBEDDING_BASE_URL"),
            gee_project_id=_env("GEE_PROJECT_ID") or _env("APP3_GEE_PROJECT_ID"),
            gis_cache_dir=_env("APP3_GIS_CACHE_DIR"),
            gis_use_cache=gis_use_cache,
            explainer_llm=explainer_llm,
            plan_use_llm=plan_use_llm,
            backoff_max_seconds=backoff_max_seconds,
            backoff_jitter_ratio=backoff_jitter_ratio,
            gis_nominatim_enabled=gis_nominatim_enabled,
            nominatim_user_agent=_env("APP3_NOMINATIM_USER_AGENT"),
            geo_fallback_nominatim=geo_fallback_nominatim,
            executor_parallel=executor_parallel,
            executor_parallel_workers=executor_parallel_workers,
            data_dir=data_dir,
            globeland30_dir=globeland30_dir,
            processed_data_dir=processed_data_dir,
            raw_admin_boundary_dir=raw_admin_boundary_dir,
            processed_admin_boundary_dir=processed_admin_boundary_dir,
            task_store_dir=task_store_dir,
            district_csv_path=district_csv_path,
        )


def settings_for_tests(**overrides: object) -> Settings:
    """构造带默认 GIS 路径的 Settings，供单测与脚本使用（不读取 .env）。"""
    base = Settings()
    if not overrides:
        return base
    return replace(base, **overrides)  # type: ignore[arg-type]
