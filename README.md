# MCP-RAG Hexagonal

A minimal and decoupled project using hexagonal architecture:
- `domain`: models and ports
- `application`: use cases and orchestration
- `adapters`: storage, embeddings, chunking, cli, and mcp
- `bootstrap`: wiring and adapter registry for plug/unplug implementations

## Requirements
- Python 3.14+
- `pip install -r requirements.txt`

## GitCore Protocol
This project includes a GitCore-aligned baseline:
- `.git-core-protocol-version`
- `.gitcore/ARCHITECTURE.md`
- `.gitcore/AGENT_INDEX.md`
- `.gitcore/CLI_CONFIG.md`
- `.gitcore/CONTEXT_LOG.md`
- `.gitcore/features.json`

Suggested startup order for agents:
1. Read `.gitcore/ARCHITECTURE.md`
2. Check `.gitcore/features.json`
3. Run `python -m pytest -q tests`
4. Run `python scripts/rag_eval_levels.py --levels all`

## CLI Usage
### Base Commands
- `python -m cerebro_python rag-ingest --document-id doc1 --text "content..."`
- `python -m cerebro_python rag-search --query "content" --top-k 5 --min-score 0.2`
- `python -m cerebro_python rag-stats`
- `python -m cerebro_python rag-delete --document-id doc1`
- `python -m cerebro_python adapters`

### Interactive & LLM Commands (Powered by MiniMax)
- `python -m cerebro_python rag-ask -q "Pregunta sobre el contexto"` — Single-shot RAG + LLM answer.
- `python -m cerebro_python rag-chat` — Interactive multi-turn RAG chat.

### Web Search Integration (via MiniMax MCP)
- `python -m cerebro_python rag-web-ingest -q "search query"` — Searches web and ingests results.
- `python -m cerebro_python rag-web-ask -q "question"` — Search, ingest, and answer in one step.

### GitHub Repo Context Sync Skill
- `python -m cerebro_python rag-sync-repos --config scripts/skills/repo_context_sync/repos.config.json --state .gitcore/repo_context_state.json --cache-dir .cache/repo-context-repos`
- Skill manifest: `scripts/skills/repo_context_sync/skill.json`
- Config template: `scripts/skills/repo_context_sync/repos.config.example.json`
- Workflow automation: `.github/workflows/repo-context-sync.yml` (hourly + manual)

The sync command ingests only changed files between commits and stores provenance metadata (`repo_key`, `repo_commit`, `repo_path`, `repo_stack`, `fact_key`) to keep context aligned with repository history.

## MCP Usage
- `python -m cerebro_python mcp`
- `python -m cerebro_python.mcp_server_integrated --mode http --port 8001`

## Codex MCP Configuration
Use Streamable HTTP (recommended when Docker is running):

```json
{
  "mcpServers": {
    "cerebro-rag": {
      "transport": "streamable_http",
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

STDIO fallback (local process):

```json
{
  "mcpServers": {
    "cerebro-rag-stdio": {
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "cerebro_python", "mcp"]
    }
  }
}
```

CLI-first recommendation:
- If you want Codex to use MCP through CLI process management, use the STDIO config above.
- Ensure the same Python environment that has project dependencies is used by Codex.
- On Windows, if needed, use absolute interpreter path for `command` (for example your venv `python.exe`).

## Adapter Configuration (env hot-swap)
- `RAG_REPOSITORY_ADAPTER=sqlite`
- `RAG_REPOSITORY_ADAPTER=memory` (ephemeral, useful for tests/short-lived agents)
- `RAG_CHUNKER_ADAPTER=simple`
- `RAG_EMBEDDING_ADAPTER=hash|ollama`
- `RAG_RANKER_ADAPTER=hybrid`
- `RAG_MEMORY_POLICY_ADAPTER=smart|identity`
- `RAG_RERANKER_ADAPTER=heuristic|identity`
- `RAG_QUERY_REWRITER_ADAPTER=rules|identity`
- `RAG_SCOPE_STRATEGY_ADAPTER=strict|auto`
- `RAG_DB_PATH=cerebro_rag.db`
- `RAG_CHUNK_SIZE=900`
- `RAG_CHUNK_OVERLAP=150`
- `RAG_MIN_CHUNK_CHARS=24`
- `RAG_MAX_CHUNKS_PER_DOC=128`
- `RAG_SEMANTIC_WEIGHT=0.75`
- `RAG_LEXICAL_WEIGHT=0.25`
- `RAG_RRF_K=50`
- `RAG_MMR_LAMBDA=0.75`
- `RAG_RERANK_BASE_WEIGHT=0.7`
- `RAG_RERANK_LEXICAL_WEIGHT=0.3`
- `RAG_RERANK_PHRASE_BOOST=0.1`
- `RAG_RETRIEVAL_MULTIPLIER=4`
- `RAG_MIN_SCORE=-1.0`
- `OLLAMA_URL=http://ollama:11434`
- `OLLAMA_MODEL=nomic-embed-text`

## Cognitive Memory System (Cerebro Cognitivo)

Biologically-inspired 4-level hierarchical memory inspired by H-MEM, MemoryBank, HippoRAG, CoALA, and Generative Agents research.

```
L0  SENSORY  — raw session buffer (no embedding)
L1  WORKING  — active context for current task (N slots)
L2  EPISODIC — persisted events with Ebbinghaus temporal decay
L3  SEMANTIC — distilled facts synthesised by LLM (permanent)
```

Memory moves **up** (promotion) when `cognitive_score ≥ threshold` or access frequency is high.
Memory moves **down** (demotion / forgetting) when score decays below `forget_threshold`.

```
cognitive_score = w_rec·recency + w_imp·importance + w_rel·relevance + w_freq·frequency
```

### Cognitive & LLM Config (.env)
- `MINIMAX_API_KEY=`            — Your MiniMax API key.
- `MINIMAX_API_HOST=https://api.minimax.io`
- `MINIMAX_MODEL=MiniMax-M2.5`  — Anthropic-compatible model name.
- `RAG_COGNITIVE_ENABLED=true`
- `RAG_COGNITIVE_WM_SLOTS=20`   — L1 (Working Memory) capacity.
- `RAG_COGNITIVE_DECAY_LAMBDA=0.02` — Ebbinghaus decay rate.
- `RAG_COGNITIVE_PROMOTE_L1_THRESHOLD=0.6`
- `RAG_COGNITIVE_CONSOLIDATE_THRESHOLD=0.75`

Copy `.env.example` to `.env` and fill in your MiniMax credentials. The system degrades gracefully (importance defaults to 0.5, consolidation to text join) when no API key is set.


Active RAG techniques (pure Python, low coupling):
- Hybrid ranking: semantic + lexical
- Robust fusion: Reciprocal Rank Fusion (RRF)
- Diversification: Maximal Marginal Relevance (MMR)
- Near-duplicate chunk dedupe to reduce noise
- Decoupled memory policy: short-chunk filter, normalization, dedupe, and per-document cap
- Optional second-stage reranking: lexical coverage + phrase boost over base relevance
- Optional pre-retrieval query rewrite: synonym expansion for higher recall
- Runtime relevance control: query-time `--min-score` and global `RAG_MIN_SCORE`
- Scope isolation by project/environment with optional cross-environment expansion
- Adaptive scope strategy via `scope_mode=strict|custom|auto`
- Temporal consistency controls: `event_time_at`, `ingested_before`, and latest-fact resolution by `fact_key`

## Evaluation Scripts
- Local multi-level evaluation:
  `python scripts/rag_eval_levels.py --levels all`
- Docker scoped smoke checks:
  `powershell -ExecutionPolicy Bypass -File scripts/run_rag_eval_in_docker.ps1`

## Docker (FastMCP + Ollama embeddings)
- `docker compose up -d --build`
- `docker exec mcp_rag_ollama ollama pull nomic-embed-text`
- `docker exec mcp_rag_server python -m cerebro_python rag-ingest --document-id d1 --text "test text"`
- `docker exec mcp_rag_server python -m cerebro_python rag-search --query "test" --top-k 3`

Exposed tools:
- `rag_ingest`
- `rag_search`
- `rag_delete`
- `rag_stats`
- `get_server_info`

## Tests
- `python -m pytest -q tests`
