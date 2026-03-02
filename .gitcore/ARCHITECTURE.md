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

## Planned Issue: `issue-rag-data-platform-2026-03-02`

Status: `draft`  
Execution: `not started`  
Goal: Define a business-aligned architecture to operate a multi-repo RAG data platform with segmented vector shards and on-demand retrieval.

### Business Requirements

1. Context fidelity
- Every retrieved chunk must keep provenance: `repo`, `path`, `branch`, `commit`, `stack`.
- Retrieval must support latest-fact semantics by stable keys.

2. Stack isolation
- Rust, Python, TypeScript, and other stacks must remain isolated by default.
- Cross-stack retrieval must be explicit and auditable.

3. Cost control
- Avoid full corpus downloads.
- Enable on-demand segment downloads only for relevant query scope.
- Keep growth within monthly storage/bandwidth budget.

4. Operational simplicity
- GitHub-native orchestration first.
- Deterministic rebuild from manifests and immutable shard files.

### Functional Requirements

- Incremental ingestion from git commit ranges (`before..after`).
- Rename/delete handling for repository sync.
- Segment manifests that map query scope to shard URIs.
- Shard-level checksums and metadata for reproducibility.
- Support both local storage and remote data backends.

### Non-Functional Requirements

- Scalability: shard-first storage, no monolithic mutable index as source of truth.
- Reliability: resumable sync jobs and idempotent upsert/delete behavior.
- Security: no plaintext secrets in stored records; secret references only.
- Traceability: each shard linked to source commits and ingestion time.

### Target Architecture

1. Control Plane (GitHub repo)
- Workflow orchestration, sync policies, manifests, schema contracts.
- Issue and decision tracking in `.gitcore/features.json`.

2. Data Plane (segmented storage by stack)
- Option A: GitHub data repos per stack (`rag-data-rust`, `rag-data-python`).
- Option B: Hybrid with Hugging Face data lake for large shard volumes.

3. Query-Time Planner
- Resolve intent -> stack scope -> manifest lookup -> selective shard load.
- Inject only relevant chunks into runtime RAG.

### Data Contract (v1)

- Partition: `stack/language/repository/branch/date/shard`.
- Shard format: compressed `parquet`.
- Required shard metadata:
  - `shard_id`, `stack`, `repo`, `branch`, `commit_from`, `commit_to`
  - `embedding_model`, `vector_dim`, `row_count`, `checksum`, `uri`, `created_at`
- Required record metadata:
  - `chunk_id`, `text`, `embedding`, `repo`, `path`, `commit`, `stack`, `language`, `fact_key`, `updated_at`

### Delivery Phases

1. Governance and schema approval
2. Control plane implementation
3. Rust pilot (business-critical repos + direct dependencies)
4. Cost/performance gate: GitHub-only vs GitHub+HF
5. Multi-stack rollout

### Acceptance Criteria

- Incremental sync processes changed files only.
- Retrieval downloads only required shards for scoped query.
- Provenance is present for every returned chunk.
- Full index can be reconstructed from manifests + shards.
- Monthly cost remains inside approved threshold.

### Current Status Snapshot (2026-03-02)

- Implemented:
  - Incremental repo sync command and workflow (`rag-sync-repos` + `.github/workflows/repo-context-sync.yml`).
  - Stack-aware metadata ingestion with commit/path provenance.
  - Cognitive memory core components and unit tests.
- Pending:
  - Default runtime wiring for cognitive cycle in RAG/CLI/MCP path.
  - Production repository catalog by stack (non-local URLs for CI automation).
  - Formal decision gate for GitHub-only vs GitHub + Hugging Face data plane.
