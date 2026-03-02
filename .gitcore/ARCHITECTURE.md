---
title: "System Architecture"
type: ARCHITECTURE
id: "arch-mcp-rag"
created: 2026-03-02
updated: 2026-03-02
agent: codex
model: gpt-5
requested_by: user
summary: |
  Minimal hexagonal RAG architecture for coding agents over CLI and MCP.
keywords: [architecture, rag, mcp, cli, hexagonal]
tags: ["#architecture", "#rag", "#mcp", "#hexagonal"]
project: MCP-RAG
---

# Architecture

## Critical Decisions

| # | Category | Decision | Rationale | Never |
|---|----------|----------|-----------|-------|
| 1 | Runtime | Python-only core logic | Minimal complexity and portability | Multi-runtime orchestration |
| 2 | Boundary | Hexagonal ports/adapters | Swap logic without editing use-cases | Adapter logic in application layer |
| 3 | Interface | CLI + FastMCP only | Agent-first integration surface | Extra API/gateway layers |
| 4 | Retrieval | Scoped by `project_id` + `environment_id` | Avoid cross-project contamination | Unscoped global retrieval |
| 5 | Memory | Temporal + latest-fact resolution | Reduce stale/contradictory context | Blind retrieval of old facts |

## Stack

- Language: Python 3.14+ (project target)
- Storage: SQLite (default), In-memory (ephemeral)
- MCP: FastMCP (`stdio` and streamable HTTP)
- Embeddings: Hash (default), Ollama (optional)
- Deployment: Docker Compose

## Layers

- `domain`: data models + ports
- `application`: `RagService` use-cases
- `adapters`: chunking, embeddings, ranking, policy, reranking, query rewrite, scope strategy, cli, mcp, storage
- `bootstrap`: adapter registry + runtime wiring

## Retrieval Flow

1. Optional query rewrite (`query_rewriter`)
2. Scope filtering (`project_id`, `environment_id`, `scope_mode`)
3. Temporal filtering (`event_time_at`, `ingested_before`)
4. Hybrid ranking + optional reranking
5. Fact conflict handling (`fact_key`, latest-wins)
6. Score threshold filtering

## Reliability Rules

- Default `scope_mode` is `strict`
- `custom` mode expands only with explicit include list
- `auto` mode expands with lightweight intent rules
- Keep adapters pure and dependency-light

