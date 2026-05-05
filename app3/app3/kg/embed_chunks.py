"""离线：为 :Chunk 写入 embedding（OpenAI 兼容 API）；须先导入 seed.cypher 并创建向量索引。"""

from __future__ import annotations

import argparse
import logging
import sys

from app3.config import Settings
from app3.kg.embeddings import embed_texts
from app3.kg.neo4j_client import build_neo4j_client_from_settings

logger = logging.getLogger(__name__)


def upsert_chunk_embeddings(*, settings: Settings) -> int:
    client = build_neo4j_client_from_settings(settings)
    if client is None:
        raise RuntimeError("NEO4J_URI 未配置或 neo4j 未安装。")
    try:
        rows = client.fetch_chunks_for_embedding()
        if not rows:
            logger.warning("库中无 Chunk 节点或均无 text，请先执行 seed.cypher。")
            return 0
        texts = [str(r["text"]) for r in rows]
        vectors = embed_texts(texts, settings=settings)
        if len(vectors) != len(rows):
            raise RuntimeError("嵌入返回条数与 Chunk 不一致。")
        n = 0
        for row, emb in zip(rows, vectors, strict=True):
            cid = row.get("chunk_id")
            if not cid:
                continue
            client.write_chunk_embedding(str(cid), emb)
            n += 1
        logger.info("已写入 %s 条 Chunk 的 embedding。", n)
        return n
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    argparse.ArgumentParser(description="为 Neo4j Chunk 节点写入向量嵌入。").parse_args(argv)
    settings = Settings.from_env()
    try:
        upsert_chunk_embeddings(settings=settings)
    except RuntimeError as e:
        logger.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
