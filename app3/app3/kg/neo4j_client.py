"""Neo4j Bolt 封装：工具路径为参数化 Cypher；形态 C 与离线脚本另含写入与向量检索。"""

from __future__ import annotations

import logging
from typing import Any

from app3.config import Settings

logger = logging.getLogger(__name__)

try:
    from neo4j import Driver, GraphDatabase
except ImportError:  # pragma: no cover - optional until pip install neo4j
    Driver = Any  # type: ignore[misc,assignment]
    GraphDatabase = None  # type: ignore[misc,assignment]


class Neo4jClient:
    """参数化 Bolt 封装：工具路径仅暴露模板化只读 Cypher；形态 C 另含向量检索与离线写入接口。"""

    def __init__(self, driver: Any, *, database: str | None = None) -> None:
        self._driver = driver
        self._database = database

    def close(self) -> None:
        self._driver.close()

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def resolve_region(self, query_text: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """按名称或代码模糊匹配 Region。"""
        cypher = """
        MATCH (r:Region)
        WHERE toLower(r.name) CONTAINS toLower($q)
           OR r.region_id = $q
           OR ($code IS NOT NULL AND r.region_id CONTAINS $code)
        RETURN r.region_id AS region_id, r.name AS name, r.admin_level AS admin_level
        LIMIT $limit
        """
        q = (query_text or "").strip()
        code = None
        if len(q) > 2 and q.upper() == q.replace("-", "").replace("_", ""):
            code = q
        with self._driver.session(database=self._database) as session:
            result = session.run(
                cypher,
                {"q": q, "code": code, "limit": int(limit)},
            )
            return [dict(record) for record in result]

    def operator_dependencies(self, operator_name: str) -> dict[str, Any]:
        """返回某 Operator 的 REQUIRES 目标与 USES_DATASET。"""
        cypher = """
        MATCH (o:Operator {name: $name})
        OPTIONAL MATCH (o)-[:REQUIRES]->(d)
        OPTIONAL MATCH (o)-[:USES_DATASET]->(ds:Dataset)
        RETURN o.name AS op,
               collect(DISTINCT d) AS dep_nodes,
               collect(DISTINCT ds.dataset_id) AS datasets
        """
        with self._driver.session(database=self._database) as session:
            record = session.run(cypher, {"name": operator_name.strip()}).single()
            if record is None or record.get("op") is None:
                return {"operator": operator_name, "dependencies": [], "datasets": [], "found": False}
            deps: list[dict[str, Any]] = []
            for n in record["dep_nodes"]:
                if n is None:
                    continue
                nid = n.get("name") or n.get("dataset_id") or n.get("region_id")
                if nid:
                    deps.append({"id": str(nid), "labels": list(n.labels)})
            dsets = [x for x in record["datasets"] if x]
            return {
                "operator": record["op"],
                "dependencies": deps,
                "datasets": dsets,
                "found": True,
            }

    def fetch_chunks_for_embedding(self) -> list[dict[str, Any]]:
        """供离线 embed 脚本：列出带 text 的 Chunk。"""
        cypher = """
        MATCH (c:Chunk)
        WHERE c.text IS NOT NULL AND trim(toString(c.text)) <> ''
        RETURN c.chunk_id AS chunk_id, c.text AS text
        ORDER BY chunk_id
        """
        with self._driver.session(database=self._database) as session:
            return [dict(record) for record in session.run(cypher)]

    def write_chunk_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        """写入 Chunk.embedding（离线脚本；维度须与向量索引一致）。"""
        cypher = """
        MATCH (c:Chunk {chunk_id: $chunk_id})
        SET c.embedding = $embedding
        """
        with self._driver.session(database=self._database) as session:
            session.run(cypher, {"chunk_id": chunk_id, "embedding": embedding})

    def vector_query_chunks(
        self,
        *,
        index_name: str,
        embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """db.index.vector.queryNodes 包装。"""
        cypher = """
        CALL db.index.vector.queryNodes($indexName, $topK, $embedding)
        YIELD node AS c, score
        RETURN c.chunk_id AS chunk_id, c.text AS text, score AS score
        """
        with self._driver.session(database=self._database) as session:
            return [dict(r) for r in session.run(cypher, {"indexName": index_name, "topK": int(top_k), "embedding": embedding})]

    def graphrag_expand_subgraph(self, chunk_ids: list[str]) -> list[dict[str, Any]]:
        """
        自 Chunk 经 DESCRIBES 锚到实体，再展开 REQUIRES / USES_DATASET / PART_OF（出边 1 跳）。
        返回扁平行，供压缩为 kg_evidence。
        """
        if not chunk_ids:
            return []
        cypher = """
        UNWIND $chunk_ids AS cid
        MATCH (c:Chunk {chunk_id: cid})-[:DESCRIBES]->(anchor)
        OPTIONAL MATCH (anchor)-[r:REQUIRES|USES_DATASET|PART_OF]->(t)
        RETURN DISTINCT
          cid AS chunk_id,
          c.text AS chunk_text,
          head(labels(anchor)) AS anchor_label,
          coalesce(anchor.name, anchor.region_id) AS anchor_id,
          type(r) AS rel_type,
          head(labels(t)) AS target_label,
          coalesce(t.name, t.region_id, t.dataset_id) AS target_id
        """
        with self._driver.session(database=self._database) as session:
            return [dict(r) for r in session.run(cypher, {"chunk_ids": chunk_ids})]

    def count_chunks_with_embedding(self) -> int:
        """具备 embedding 的 Chunk 数量（真实环境检测用）。"""
        cypher = """
        MATCH (c:Chunk)
        WHERE c.embedding IS NOT NULL
        RETURN count(c) AS n
        """
        with self._driver.session(database=self._database) as session:
            rec = session.run(cypher).single()
            if rec is None:
                return 0
            return int(rec.get("n") or 0)

    def count_chunks_total(self) -> int:
        cypher = "MATCH (c:Chunk) RETURN count(c) AS n"
        with self._driver.session(database=self._database) as session:
            rec = session.run(cypher).single()
            return int(rec.get("n") or 0) if rec else 0

    def has_vector_index_named(self, index_name: str) -> bool:
        """SHOW INDEXES 中是否存在该名称的索引（向量索引名须与创建时一致）。"""
        cypher = """
        SHOW INDEXES YIELD name
        WHERE name = $name
        RETURN count(*) AS n
        """
        with self._driver.session(database=self._database) as session:
            try:
                rec = session.run(cypher, {"name": index_name}).single()
            except Exception:  # noqa: BLE001 — 旧版语法兜底
                return False
            return int(rec.get("n") or 0) > 0 if rec else False


def build_neo4j_client_from_settings(settings: Settings) -> Neo4jClient | None:
    """若未配置 NEO4J_URI 则返回 None（Tools 不注册）。"""
    if GraphDatabase is None:
        logger.warning("neo4j package not installed; KG tools disabled.")
        return None
    uri = settings.neo4j_uri
    if not uri:
        return None
    user = settings.neo4j_user or "neo4j"
    password = settings.neo4j_password or ""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return Neo4jClient(driver, database=settings.neo4j_database)
