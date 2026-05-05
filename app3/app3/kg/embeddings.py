"""OpenAI 兼容嵌入 API — graphrag 与离线 embed_chunks 共用。"""

from __future__ import annotations

from typing import Any


def embed_texts(texts: list[str], *, settings: Any) -> list[list[float]]:
    """返回与 texts 同序的向量列表。

    嵌入专用密钥：优先 EMBEDDING_API_KEY + EMBEDDING_BASE_URL（可与 Moonshot 对话密钥分流），
    否则回落 OPENAI_API_KEY + OPENAI_BASE_URL。
    """
    if not texts:
        return []
    api_key = getattr(settings, "embedding_api_key", None) or getattr(settings, "openai_api_key", None)
    if not api_key:
        raise RuntimeError("未设置 OPENAI_API_KEY 或 EMBEDDING_API_KEY，无法计算 embedding。")
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("请安装 openai 包。") from e

    base_url = getattr(settings, "embedding_base_url", None) or getattr(settings, "openai_base_url", None)
    client = OpenAI(api_key=api_key, base_url=base_url or None)
    dim = int(getattr(settings, "embedding_dimensions", 1536) or 1536)
    model = getattr(settings, "embedding_model", "text-embedding-3-small")
    kwargs: dict[str, Any] = {"model": model, "input": texts}
    if dim and str(model).startswith("text-embedding-3"):
        kwargs["dimensions"] = dim
    resp = client.embeddings.create(**kwargs)
    ordered = sorted(resp.data, key=lambda x: x.index)
    return [list(item.embedding) for item in ordered]


def embed_query_text(text: str, *, settings: Any) -> list[float]:
    vecs = embed_texts([text], settings=settings)
    return vecs[0] if vecs else []
