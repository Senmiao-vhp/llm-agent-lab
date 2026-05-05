"""真实环境 GraphRAG 连通性检测：Neo4j + 向量索引 + Chunk 嵌入 + 端到端检索。

配置：复制仓库 ``app3/.env.example`` 为 ``app3/.env`` 并填写（或由环境变量注入）。

用法（在 app3 目录已 ``pip install -e .``）::

    python -m app3.kg.validate_graphrag

导入 seed.cypher、vector_index.cypher 后运行 ``python -m app3.kg.embed_chunks`` 写入向量。

说明：本脚本在调用 ``graphrag_retrieve`` 时会 **临时将 graph_rag_enabled 视为 True**，
以便在未设置 GRAPH_RAG_ENABLED 时仍能完成端到端检测；运行时 Agent 仍依赖环境变量开关。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import replace

from app3.config import Settings
from app3.kg.graphrag import graphrag_retrieve
from app3.kg.neo4j_client import build_neo4j_client_from_settings

logger = logging.getLogger(__name__)


def run_prechecks(settings: Settings, client: object) -> tuple[bool, list[str]]:
    """返回 (全部通过, 文本行列表)。"""
    lines: list[str] = []
    ok_all = True

    assert hasattr(client, "verify_connectivity")
    try:
        client.verify_connectivity()
        lines.append("[ok] Neo4j Bolt 连通")
    except Exception as exc:  # noqa: BLE001
        ok_all = False
        lines.append(f"[fail] Neo4j 连通: {exc}")
        return ok_all, lines

    n_total = client.count_chunks_total()
    n_emb = client.count_chunks_with_embedding()
    lines.append(f"[info] Chunk 节点总数={n_total}, 已写入 embedding={n_emb}")
    if n_total == 0:
        ok_all = False
        lines.append("[fail] 无 Chunk：请先执行 kg/data/seed.cypher")
    elif n_emb == 0:
        ok_all = False
        lines.append("[fail] Chunk 尚无 embedding：请运行 python -m app3.kg.embed_chunks")

    ix_name = settings.neo4j_chunk_vector_index
    has_ix = client.has_vector_index_named(ix_name)
    if has_ix:
        lines.append(f"[ok] 向量索引存在: {ix_name}")
    else:
        ok_all = False
        lines.append(
            f"[fail] 未找到向量索引「{ix_name}」：请执行 kg/data/vector_index.cypher（维度须与 EMBEDDING_DIMENSIONS 一致）"
        )

    return ok_all, lines


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="GraphRAG 真实环境端到端校验")
    p.add_argument(
        "--query",
        default="成都市郫都区 耕地 NDVI 变化检测",
        help="用于向量检索与扩展的测试问句",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="向量召回数量",
    )
    args = p.parse_args(argv)

    settings = Settings.from_env()
    if not (settings.openai_api_key or settings.embedding_api_key):
        logger.error("缺少 OPENAI_API_KEY 或 EMBEDDING_API_KEY。")
        return 2

    client = build_neo4j_client_from_settings(settings)
    if client is None:
        logger.error("缺少 NEO4J_URI 或 neo4j 驱动不可用。")
        return 2

    try:
        pre_ok, pre_lines = run_prechecks(settings, client)
        for line in pre_lines:
            print(line)
        if not pre_ok:
            logger.error("前置检查未通过，跳过端到端检索。")
            return 1

        # 校验专用：强制走 GraphRAG 逻辑（与 GRAPH_RAG_ENABLED 环境变量解耦）
        eff = replace(settings, graph_rag_enabled=True)
        print("[info] graphrag_retrieve 使用 graph_rag_enabled=True（校验脚本专用）")

        out = graphrag_retrieve(
            args.query,
            top_k=args.top_k,
            settings=eff,
            client=client,
        )

        status = out.get("status")
        print(f"[result] status={status}")
        print(json.dumps(out, ensure_ascii=False, indent=2))

        evid = out.get("kg_evidence") or []
        if status == "ok" and evid:
            print("[ok] 端到端成功：kg_evidence 非空")
            return 0
        if status == "ok" and not evid:
            print("[warn] 检索成功但 kg_evidence 为空（可能问句与 Chunk 语义不匹配）")
            return 0
        if status == "placeholder":
            print("[fail] 仍为 placeholder")
            return 3
        print(f"[fail] status={status}, message={out.get('message')}")
        return 4 if status == "error" else 3
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
