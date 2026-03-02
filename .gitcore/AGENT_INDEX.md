---
title: "Agent Index"
type: INDEX
id: "index-mcp-rag-agents"
created: 2026-03-02
updated: 2026-03-02
agent: codex
model: gpt-5
requested_by: user
summary: |
  Routing guide for agents working on MCP-RAG with strict isolation and minimal complexity.
keywords: [agents, routing, rag, mcp]
tags: ["#agents", "#routing", "#rag"]
project: MCP-RAG
---

# Agent Index

## Routing Rules

1. If request is architecture/decoupling: use Hexagonal Maintainer workflow.
2. If request is retrieval quality: use Retrieval Tuner workflow.
3. If request is deployment/integration: use MCP Runtime workflow.
4. If request is context retrieval or code-history investigation: use Memory Ops workflow.

## Workflows

| Workflow | Primary Scope | Output |
|----------|----------------|--------|
| Hexagonal Maintainer | Ports, adapters, container wiring | Decoupled implementation |
| Retrieval Tuner | Ranking, reranking, rewrite, policy, scope strategy | Better precision/recall |
| MCP Runtime | CLI/MCP transport, Docker, health checks | Operational MCP endpoint |
| Evaluation Runner | Tests and eval scripts | Objective pass/fail metrics |
| Memory Ops | CLI/MCP memory routing + git-process history ingestion | Scoped context and traceable history |

## Non-Negotiables

- Keep default retrieval scoped and non-mixing.
- Prefer pure Python over new dependencies.
- Avoid adding non-essential runtime services.
- Keep CLI and MCP parity for new features.
