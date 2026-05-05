// Neo4j 最小示例：耕地/GIS 编排演示（形态 A）
// 用法：neo4j-admin database load ... 或 cypher-shell -f seed.cypher

CREATE CONSTRAINT region_id_unique IF NOT EXISTS
FOR (r:Region) REQUIRE r.region_id IS UNIQUE;

CREATE CONSTRAINT operator_name_unique IF NOT EXISTS
FOR (o:Operator) REQUIRE o.name IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;

MERGE (r1:Region {region_id: 'CN-SC-CD-PD'})
  ON CREATE SET r1.name = '成都市郫都区', r1.admin_level = 'district';
MERGE (r2:Region {region_id: 'CN-SC-CD'})
  ON CREATE SET r2.name = '成都市', r2.admin_level = 'city';
MERGE (r1)-[:PART_OF]->(r2);

MERGE (o1:Operator {name: 'resolve_geometry'})
  ON CREATE SET o1.description = '将行政区名称解析为可计算边界';
MERGE (o2:Operator {name: 'calculate_ndvi'})
  ON CREATE SET o2.description = '计算 NDVI 或加载指数';
MERGE (o3:Operator {name: 'detect_change'})
  ON CREATE SET o3.description = '耕地/植被变化检测';

MERGE (d1:Dataset {dataset_id: 'S2_L2A'})
  ON CREATE SET d1.name = 'Sentinel-2 L2A';
MERGE (o2)-[:USES_DATASET]->(d1);

MERGE (o3)-[:REQUIRES {order: 1}]->(o1);
MERGE (o3)-[:REQUIRES {order: 2}]->(o2);
MERGE (o2)-[:REQUIRES {order: 1}]->(o1);

// 形态 C：Chunk 文本（embedding 由 python -m app3.kg.embed_chunks 写入）
// 每条独立语句，兼容 cypher-shell 按语句分隔执行（跨语句无变量延续）。
MERGE (ch:Chunk {chunk_id: 'chunk_op_resolve_geometry'})
  ON CREATE SET ch.text = 'resolve_geometry 算子：将行政区名称解析为可计算几何边界，是 NDVI 与变化检测的前置步骤。'
WITH ch
MATCH (op:Operator {name: 'resolve_geometry'})
MERGE (ch)-[:DESCRIBES]->(op);

MERGE (ch:Chunk {chunk_id: 'chunk_op_calculate_ndvi'})
  ON CREATE SET ch.text = 'calculate_ndvi：基于 Sentinel-2 等影像计算 NDVI 或加载植被指数，依赖 resolve_geometry 得到的空间范围。'
WITH ch
MATCH (op:Operator {name: 'calculate_ndvi'})
MERGE (ch)-[:DESCRIBES]->(op);

MERGE (ch:Chunk {chunk_id: 'chunk_op_detect_change'})
  ON CREATE SET ch.text = 'detect_change：耕地与植被变化检测；必须先完成几何解析与 NDVI 计算，依赖 resolve_geometry 与 calculate_ndvi。'
WITH ch
MATCH (op:Operator {name: 'detect_change'})
MERGE (ch)-[:DESCRIBES]->(op);

MERGE (ch:Chunk {chunk_id: 'chunk_region_pd'})
  ON CREATE SET ch.text = '成都市郫都区：县级行政区，隶属于成都市，可用于区域筛选与耕地监测任务。'
WITH ch
MATCH (reg:Region {region_id: 'CN-SC-CD-PD'})
MERGE (ch)-[:DESCRIBES]->(reg);

MERGE (ch:Chunk {chunk_id: 'chunk_region_cd'})
  ON CREATE SET ch.text = '成都市：地级行政区，下辖郫都区等多个区县，适合作为上级行政区划查询。'
WITH ch
MATCH (reg:Region {region_id: 'CN-SC-CD'})
MERGE (ch)-[:DESCRIBES]->(reg);
