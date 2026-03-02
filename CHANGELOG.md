# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Changed
- Refactored `Dockerfile` and `docker-compose.yml` to inject `.env` MiniMax context securely.
- Updated documentation across `AGENTS.md`, `.gitcore/ARCHITECTURE.md`, `README.md` and `.cursorrules` to define the new architecture baseline.
- Project is officially shifting into **BETA** state until rigorous quantitative RAG benchmarks (retrieval recall, context precision, answer fidelity, web-hallucination rates) confirm the maturity of the Cognitive Memoria system.
