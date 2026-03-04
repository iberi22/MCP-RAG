# MCP-RAG (Beta)
> **Note:** The project is currently in Beta phase until full functionality is proven with comprehensive RAG evaluation benchmarks.

A minimalist, hexagonal-architecture RAG (Retrieval-Augmented Generation) system built for AI coding agents.
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
- `python -m cerebro_python rag-memory-plan -q "investiga regresion en auth" --project-id alpha --environment-id dev`
- `python -m cerebro_python rag-stats`
- `python -m cerebro_python rag-delete --document-id doc1`
- `python -m cerebro_python adapters`

### Interactive & LLM Commands (Powered by MiniMax)
- `python -m cerebro_python rag-ask -q "Pregunta sobre el contexto"` — Single-shot RAG + LLM answer.
- `python -m cerebro_python rag-chat` — Interactive multi-turn RAG chat.

### Web Search Integration (via MiniMax MCP)
- `python -m cerebro_python rag-web-ingest -q "search query"` — Searches web and ingests results.
- `python -m cerebro_python rag-web-ask -q "question"` — Search, ingest, and answer in one step.

### Agent Skills & Capabilities (Root: `.agents/skills`)

We have consolidated the repository context and memory operations into a single master skill module: **`mcp_rag_memory_ops`**.

- **Skill Guide (Must Read)**: `.agents/skills/mcp_rag_memory_ops/SKILL.md`
- **Git History Ingestion**: `python .agents/skills/mcp_rag_memory_ops/git_history_ingest.py --max-commits 80 --project-id alpha --environment-id dev`
- **Repo Context Syncing**: `python -m cerebro_python rag-sync-repos --config .agents/skills/mcp_rag_memory_ops/repos.config.json --state .gitcore/repo_context_state.json --cache-dir .cache/repo-context-repos`
- **Workflow automation**: `.github/workflows/repo-context-sync.yml` (hourly + manual)

The sync command ingests only changed files between commits and stores provenance metadata (`repo_key`, `repo_commit`, `repo_path`, `repo_stack`, `fact_key`) to keep context aligned with repository history.

#### Recommendations for AI Agents Using This Implementation:
1. **Always read `SKILL.md` first**: Located at `.agents/skills/mcp_rag_memory_ops/SKILL.md`, it contains the exact playbook, CLI commands, and MCP tools available.
2. **Leverage MCP Tools**: Directly call `rag_search` or `rag_memory_plan` via MCP for real-time context before writing or modifying code.
3. **Use strict scoping**: Always default to strict scoping (`scope_mode = "strict"`) to prevent polluting results with irrelevant environments unless explicitly requested.
4. **Historical root cause analysis**: When debugging regressions, use the `git_history_ingest.py` script to index the commit history, then use `rag_search` to understand *why* a past architectural decision was made.

### Hybrid Retrieval Strategy (Code + Large Documents)

This project now formalizes a **hybrid retrieval strategy**:
- **Code-first (agentic/structured retrieval)** for exact identifiers, symbols, files, and stack-aware repository navigation.
- **Semantic-first (vector retrieval)** for unstructured documentation, incident notes, specs, and web-ingested knowledge.

#### Enhanced Codebase Management Capabilities
- Symbol indexing and exact symbol retrieval:
  - `python -m cerebro_python index-symbol-file --file <path>`
  - `python -m cerebro_python search-symbols -q "<symbol-or-query>"`
  - `python -m cerebro_python get-symbol --symbol-id "<file::qualified_name#kind>"`
  - `python -m cerebro_python get-file-outline --file <path>`
- Incremental repository context sync:
  - `python -m cerebro_python rag-sync-repos --config .agents/skills/mcp_rag_memory_ops/repos.config.json --state .gitcore/repo_context_state.json --cache-dir .cache/repo-context-repos`
- Repository registration + optional immediate sync:
  - `python -m cerebro_python rag-register-repo --url "file:///absolute/path/to/repo" --branch main --stack python --project-id <project> --environment-id dev --sync`

#### Why this matters
- For code queries, exact/structured retrieval avoids semantic drift and preserves path/symbol precision.
- For large unstructured corpora (including multi-GB documents), semantic retrieval remains the scalable default.
- The roadmap now targets both workloads together instead of forcing one retrieval method for every query.

## MCP Usage
- `python -m cerebro_python mcp`
- `python -m cerebro_python.mcp_server_integrated --mode http --port 8001`
- Health endpoints (HTTP mode):
  - `http://localhost:8001/health`
  - `http://localhost:8001/healthz`

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
- `RAG_RERANKER_ADAPTER=heuristic|minimax|identity`
- `RAG_QUERY_REWRITER_ADAPTER=rules|minimax|identity`
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
- `RAG_LLM_REWRITE_MAX_TOKENS=96`
- `RAG_LLM_RERANK_TOP_N=20`
- `RAG_LLM_RERANK_WEIGHT=0.45`
- `RAG_RETRIEVAL_MULTIPLIER=5`
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

### Cognitive & LLM Config (in `.env`)
- `RAG_AUTO_INDEX_CODE=true` (Automatically triggers a background Git repository sync on startup)
- `RAG_CHUNKER_ADAPTER=ast` (Uses the high-performance Rust tree-sitter chunker for code)
- `RAG_REPOSITORY_ADAPTER=sqlite` (Uses local SQLite for persistence)
- `MINIMAX_API_KEY=`            — Your MiniMax API key.
- `MINIMAX_API_HOST=https://api.minimax.io`
- `MINIMAX_MODEL=MiniMax-M2.5`  — Anthropic-compatible model name.
- `RAG_COGNITIVE_ENABLED=true`
- `RAG_COGNITIVE_WM_SLOTS=20`   — L1 (Working Memory) capacity.
- `RAG_COGNITIVE_DECAY_LAMBDA=0.02` — Ebbinghaus decay rate.
- `RAG_COGNITIVE_PROMOTE_L1_THRESHOLD=0.6`
- `RAG_COGNITIVE_CONSOLIDATE_THRESHOLD=0.75`
- `RAG_COGNITIVE_BACKGROUND_ENABLED=true` — runs periodic consolidation/decay jobs.
- `RAG_COGNITIVE_CONSOLIDATION_INTERVAL_MIN=10`
- `RAG_COGNITIVE_DECAY_INTERVAL_MIN=60`

Copy `.env.example` to `.env` and fill in your MiniMax credentials. The system degrades gracefully (importance defaults to 0.5, consolidation to text join) when no API key is set.


Active RAG techniques (pure Python, low coupling):
- Hybrid ranking: semantic + lexical
- Robust fusion: Reciprocal Rank Fusion (RRF)
- Diversification: Maximal Marginal Relevance (MMR)
- Near-duplicate chunk dedupe to reduce noise
- Decoupled memory policy: short-chunk filter, normalization, dedupe, and per-document cap
- Optional second-stage reranking: lexical coverage + phrase boost over base relevance
- Optional MiniMax reranker: LLM relevance scoring fused with base ranking
- Optional pre-retrieval query rewrite: rules-based synonym expansion or MiniMax semantic expansion
- Runtime relevance control: query-time `--min-score` and global `RAG_MIN_SCORE`
- Scope isolation by project/environment with optional cross-environment expansion
- Adaptive scope strategy via `scope_mode=strict|custom|auto`
- Temporal consistency controls: `event_time_at`, `ingested_before`, and latest-fact resolution by `fact_key`

## Evaluation Scripts
- Local multi-level evaluation:
  `python scripts/rag_eval_levels.py --levels all`
- Docker scoped smoke checks:
  `powershell -ExecutionPolicy Bypass -File scripts/run_rag_eval_in_docker.ps1 -Container cerebro_mcp`
- **Multi-Agent Swarm Orchestrator**:
  `python scripts/cerebro_swarm_run.py --repo-key langchain-ai/langchain --concurrency 10`
  *(See `scripts/benchmark/BENCHMARK_GUIDE.md` or the generic `rag_swarm_benchmark/` package for details).*

## Docker (FastMCP + Ollama embeddings)
- `docker compose up -d --build`
- `docker exec mcp_rag_ollama ollama pull nomic-embed-text`
- `docker exec cerebro_mcp python -m cerebro_python rag-ingest --document-id d1 --text "test text"`
- `docker exec cerebro_mcp python -m cerebro_python rag-search --query "test" --top-k 3`

Security note:
- Avoid sharing terminal output that expands secret environment variables (for example, fully rendered compose configs in CI logs).

Exposed tools:
- `rag_ingest`
- `rag_search`
- `rag_delete`
- `rag_memory_plan`
- `rag_stats`
- `get_server_info`

## Tests
- `python -m pytest -q tests`

## Protocol Issue Tracking
- Permanent issue records are tracked in `.gitcore/features.json`.
- Active architecture draft: `issue-rag-data-platform-2026-03-02`.
- New 2026-03-04 roadmap issues:
  - `#4` research: valoración RAG 2026 (código vs no estructurado, 2GB+)
  - `#5` ingesta lazy/streaming para documentos >2GB
  - `#6` embeddings por lotes con retries y aislamiento por batch
  - `#7` retrieval escalable con prefiltro + ANN/vector index
  - `#8` planner híbrido (agentic code search + semantic docs)
  - `#9` generación grounded con citas obligatorias y política anti-alucinación
  - `#10` benchmark híbrido 2GB+ (código/documentos)
  - `#11` actualización de README para administración de codebase y estrategia híbrida

## Plan Status (Implemented vs Pending)

### Implemented
- Incremental repo sync pipeline (`rag-sync-repos`) with diff-based upsert/delete.
- GitHub Actions automation for periodic repo context sync.
- Cognitive memory core components (models, ports, adapters, service) with unit tests.

### Pending to close the business plan
- Finalize production repository catalog for stack-segmented sync (current config may be bootstrap/local).
- Define storage strategy decision gate (GitHub segmented repos vs hybrid GitHub + Hugging Face data lake).

For detailed architecture and business requirements, see `.gitcore/ARCHITECTURE.md` and `docs/GestiónCognitivadeMemoriasporLLM.md`.
