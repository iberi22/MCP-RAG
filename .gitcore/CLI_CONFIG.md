# CLI Orchestration Structure

This file defines required tools and usage priority for this project.

## Dependency Graph

| CLI Tool | Required Version | Provider | Priority |
|----------|------------------|----------|----------|
| `python` | >= 3.11 runtime, target >= 3.14 | System | Critical |
| `docker` | recent | Docker | Critical |
| `docker compose` | v2+ | Docker | Critical |
| `pytest` | project env | Python | High |
| `curl` / `Invoke-WebRequest` | system | System | Medium |

## Capability Map

### Development
- Run tests: `python -m pytest -q tests`
- Run local eval: `python scripts/rag_eval_levels.py --levels all`
- Run CLI app: `python -m cerebro_python ...`

### Runtime
- Launch stack: `docker compose up -d --build`
- Pull embedding model: `docker exec mcp_rag_ollama ollama pull nomic-embed-text`
- Docker eval: `powershell -ExecutionPolicy Bypass -File scripts/run_rag_eval_in_docker.ps1`

### MCP
- HTTP endpoint: `http://localhost:8001/mcp`
- STDIO entrypoint: `python -m cerebro_python mcp`

## Operational Defaults

- Retrieval default mode: `scope_mode=strict`
- Expansion modes: `custom` (explicit), `auto` (intent-based)
- Use `RAG_SCOPE_STRATEGY_ADAPTER=strict|auto` for behavior control

