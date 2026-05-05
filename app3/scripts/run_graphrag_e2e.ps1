# GraphRAG 端到端：拉起 Neo4j → 导入 seed / vector_index → embed_chunks → validate_graphrag
# 用法（在仓库 llm-agent-lab/app3 下）:
#   复制 .env.example 为 .env 并填写密钥后执行:
#   .\scripts\run_graphrag_e2e.ps1
# 依赖: Docker Desktop、app3/.env（见 .env.example）、嵌入 API（EMBEDDING_*）。

$ErrorActionPreference = "Stop"
$App3Root = Split-Path $PSScriptRoot -Parent
$KgData = Join-Path $App3Root "kg\data"
$App3Env = Join-Path $App3Root ".env"
if (-not (Test-Path $App3Env)) {
    Write-Error "缺少 app3/.env。请复制 app3/.env.example 为 .env 并填写 OPENAI_* / NEO4J_* / EMBEDDING_* 等。"
}

$env:APP3_ENV_FILE = $App3Env
$env:NEO4J_URI = "bolt://127.0.0.1:7687"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "graphragtest"

Write-Host "==> Docker Compose 启动 Neo4j ..."
Push-Location $App3Root
try {
    docker compose -f docker-compose.neo4j.yml up -d
} catch {
    Write-Error "Docker 不可用或未启动 Docker Desktop: $_"
}

$deadline = (Get-Date).AddMinutes(4)
$ready = $false
while ((Get-Date) -lt $deadline) {
    $t = Test-NetConnection 127.0.0.1 -Port 7687 -WarningAction SilentlyContinue
    if ($t.TcpTestSucceeded) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    Write-Error "7687 端口未就绪，请确认 Docker Desktop 已启动且容器 neo4j-graphrag-app3 在运行。"
}

Write-Host "==> 导入 seed.cypher ..."
Get-Content (Join-Path $KgData "seed.cypher") -Raw | docker exec -i neo4j-graphrag-app3 cypher-shell -u neo4j -p graphragtest --format plain | Out-Null

Write-Host "==> 导入 vector_index.cypher ..."
Get-Content (Join-Path $KgData "vector_index.cypher") -Raw | docker exec -i neo4j-graphrag-app3 cypher-shell -u neo4j -p graphragtest --format plain | Out-Null

Write-Host "==> 写入 Chunk embedding（需 EMBEDDING_* 或可用的嵌入 API）..."
python -m app3.kg.embed_chunks
if ($LASTEXITCODE -ne 0) {
    Write-Warning "embed_chunks 失败（常见原因：Moonshot 未开放嵌入 API，请配置 EMBEDDING_API_KEY + EMBEDDING_BASE_URL）。"
    Pop-Location
    exit $LASTEXITCODE
}

Write-Host "==> 端到端校验 ..."
python -m app3.kg.validate_graphrag
$code = $LASTEXITCODE
Pop-Location
exit $code
