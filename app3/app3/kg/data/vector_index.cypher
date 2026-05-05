// Neo4j 5.x：Chunk.embedding 向量索引（维度须与 EMBEDDING_DIMENSIONS / 嵌入模型一致）
// 在加载 seed.cypher 后执行一次；索引可在尚无 embedding 时创建。
// cypher-shell -f vector_index.cypher

CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
FOR (c:Chunk)
ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
  }
};
