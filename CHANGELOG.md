# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.2-beta] - 2026-03-03

### Added
- Added HTTP health endpoints in integrated server mode: `/health` and `/healthz`.

### Changed
- Refactored `cerebro_python.mcp_server_integrated` to avoid side effects at import time.
- Updated repository auto-index default config path to `.agents/skills/mcp_rag_memory_ops/repos.config.json` with legacy fallback support.
- Redirected auto-index runtime logs to `stderr` to preserve clean JSON output from CLI commands.
- Tuned balanced retrieval defaults by setting `RAG_RETRIEVAL_MULTIPLIER=5`.

## [0.9.1-beta] - 2026-03-03

### Added
- Added `SimpleChunker.chunk()` as a compatibility alias to `split()` for adapters expecting a `chunk()` method.
- Added backward-compatibility alias `RagUseCases = RagService` in the application use-cases module.

### Changed
- Updated Docker compose development behavior by mounting the workspace into the container (`.:/app`) for aligned runtime code.
- Standardized smoke scripts and workflow defaults to use `cerebro_mcp` as the server container name.
- Updated README deployment commands and smoke examples to use the current container naming.

### Security
- Added operational guidance to avoid exposing expanded secret environment variables in shared logs.

## [0.9.0-beta] - 2026-03-02

### Added
- **MiniMax LLM Integration**: Added native support for MiniMax `MiniMax-M2.5-highspeed` using their Anthropic-compatible API endpoint format. Removes `anthropic` client SDK package footprint by using native `urllib`.
- **MiniMax MCP Web Search**: Added seamless subprocess execution of `minimax-coding-plan-mcp` for intelligent web research augmented via LLM.
- **Cognitive Memory System**: A new 4-tier semantic scoring model composed of:
  - Memory Levels: `Sensory`, `Working`, `Episodic`, `Semantic`.
  - Factors: Recency, Relevance, Importance, Frequency.
  - Automatically decays or promotes items during queries.
- **Semantic AST Chunker in Rust**: Developed a high-performance `tree-sitter` binaries (`tools/rust-ast-chunker`) that splits code logically (Python, Javascript, TypeScript, Rust) ensuring full classes/functions context instead of raw character counts.
- **Background Auto-Index Daemon**: Using `RAG_AUTO_INDEX_CODE=true` allows the `RagService` to silently update context via Git whenever the application starts, completely decoupled from the main thread.
- **New User CLI Commands**: Added `rag-ask`, `rag-chat`, `rag-web-ingest`, `rag-web-ask` to the core CLI for quick testing and AI-loop feedback execution.
- **MiniMax Query Rewriter Adapter**: Added `RAG_QUERY_REWRITER_ADAPTER=minimax` with deterministic fallback to `rules`.
- **MiniMax Reranker Adapter**: Added `RAG_RERANKER_ADAPTER=minimax` with blended LLM/base scoring and fallback to heuristic reranker.
- **Cognitive Background Runtime**: Added periodic scheduler (`RAG_COGNITIVE_BACKGROUND_ENABLED`) to run decay and L2→L3 consolidation autonomously.

### Changed
- Refactored `Dockerfile` and `docker-compose.yml` to inject `.env` MiniMax context securely.
- Updated documentation across `AGENTS.md`, `.gitcore/ARCHITECTURE.md`, `README.md` and `.cursorrules` to define the new architecture baseline.
- Project is officially shifting into **BETA** state until rigorous quantitative RAG benchmarks (retrieval recall, context precision, answer fidelity, web-hallucination rates) confirm the maturity of the Cognitive Memoria system.
- Updated `CognitiveService.run_consolidation` to persist L3 semantic facts as searchable `rag_chunks` in addition to cognitive metadata.
