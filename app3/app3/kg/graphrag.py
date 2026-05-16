"""形态 C：GraphRAG（Neo4j Chunk 向量 + DESCRIBES 锚定 + 子图扩展）。"""

from __future__ import annotations

from typing import Any

from app3.config import Settings
from app3.kg.embeddings import embed_query_text
from app3.kg.neo4j_client import Neo4jClient


def graphrag_retrieve_placeholder(query: str, *, top_k: int = 5) -> dict[str, Any]:
    """
    GRAPH_RAG_ENABLED 未开启或缺少 Neo4j/API 时的回落。

    启用形态 C 时需设置 GRAPH_RAG_ENABLED=true、NEO4J_*、OPENAI_API_KEY，
    并执行 seed.cypher、vector_index.cypher 与 embed_chunks。
    """
    _ = top_k
    return {
        "status": "placeholder",
        "kg_evidence": [],
        "message": (
            "GraphRAG 未启用：设置 GRAPH_RAG_ENABLED=true 并配置 NEO4J_URI、OPENAI_API_KEY；"
            "导入 seed 与 vector_index 后运行 python -m app3.kg.embed_chunks。"
        ),
        "query": query,
    }


def _pack_evidence(
    hits: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    score_by_cid: dict[str, Any] = {}
    text_by_cid: dict[str, Any] = {}
    order: list[str] = []
    for h in hits:
        cid = h.get("chunk_id")
        if not cid:
            continue
        cid = str(cid)
        if cid not in score_by_cid:
            order.append(cid)
        score_by_cid[cid] = h.get("score")
        text_by_cid[cid] = h.get("text")

    by_chunk: dict[str, list[dict[str, Any]]] = {}
    for row in raw_rows:
        cid = row.get("chunk_id")
        if not cid:
            continue
        cid = str(cid)
        edge = {
            "anchor_label": row.get("anchor_label"),
            "anchor_id": row.get("anchor_id"),
            "rel_type": row.get("rel_type"),
            "target_label": row.get("target_label"),
            "target_id": row.get("target_id"),
        }
        by_chunk.setdefault(cid, []).append(edge)

    evidence: list[dict[str, Any]] = []
    for cid in order:
        text = text_by_cid.get(cid) or ""
        evidence.append(
            {
                "chunk_id": cid,
                "score": score_by_cid.get(cid),
                "chunk_text_preview": text[:500],
                "subgraph_edges": by_chunk.get(cid, []),
            }
        )
    return evidence


def graphrag_retrieve(
    query: str,
    *,
    top_k: int = 5,
    settings: Settings,
    client: Neo4jClient | None,
) -> dict[str, Any]:
    """query → 嵌入 → Chunk 向量 Top-K → DESCRIBES 实体 → 子图边 → kg_evidence。"""
    has_embed_key = bool(
        getattr(settings, "embedding_api_key", None) or getattr(settings, "openai_api_key", None)
    )
    if not (settings.graph_rag_enabled and client is not None and has_embed_key):
        return graphrag_retrieve_placeholder(query, top_k=top_k)

    try:
        q_emb = embed_query_text((query or "").strip(), settings=settings)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "kg_evidence": [],
            "message": f"嵌入失败: {exc}",
            "query": query,
        }

    try:
        hits = client.vector_query_chunks(
            index_name=settings.neo4j_chunk_vector_index,
            embedding=q_emb,
            top_k=int(top_k),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "kg_evidence": [],
            "message": f"向量检索失败: {exc}",
            "query": query,
        }

    if not hits:
        return {
            "status": "ok",
            "kg_evidence": [],
            "message": "向量检索无命中；请确认 Chunk.embedding 已写入且向量索引名称与 NEO4J_CHUNK_VECTOR_INDEX 一致。",
            "query": query,
        }

    chunk_ids = [str(h["chunk_id"]) for h in hits if h.get("chunk_id")]
    try:
        raw = client.graphrag_expand_subgraph(chunk_ids)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "kg_evidence": [],
            "message": f"子图扩展失败: {exc}",
            "query": query,
        }

    evidence = _pack_evidence(hits, raw)
    return {
        "status": "ok",
        "kg_evidence": evidence,
        "query": query,
    }
