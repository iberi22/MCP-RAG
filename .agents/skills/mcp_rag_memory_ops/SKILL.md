---
name: mcp-rag-memory-ops
description: Comprehensive guide for RAG memory operations, including CLI usage, MCP tools, Git history ingestion, and environment evaluation scripts.
---

# 🧠 MCP RAG Memory Operations

This skill consolidates all RAG memory operations, repository context synchronization, and environment evaluation tools into a single reference point. It maintains the project's minimalist and easy-to-adopt philosophy while giving agents complete awareness of their capabilities.

Here you will learn how to efficiently interact with the project's indexed memory (RAG), utilize all MCP tools, test the RAG environment, and query the Git history for context.

---

## 🛠️ Available MCP Tools

Agents have access to a suite of RAG-specific MCP tools to directly manipulate and query the vector database without dropping to the CLI:

- **`rag_search`**: Search the database with strict or custom environment scoping.
- **`rag_memory_plan`**: Create a structured query plan to explore context before diving into deep searches.
- **`rag_ingest`**: Manually ingest specific texts, files, or facts into the knowledge base.
- **`rag_delete`**: Remove specific documents from the memory by document ID.
- **`rag_stats`**: View the current statistics, chunk counts, and health of the RAG repository.

---

## 🎯 Playbook & Intents

### 1. Quick Context Lookup (`quick_context_lookup`)
**When to use:** Point-in-time code context questions or to retrieve relevant snippets for an active task.
* **CLI**: `python -m cerebro_python rag-search --query "<query>" --top-k 8 --project-id <project> --environment-id <env> --scope-mode strict`
* **MCP**: Call the `rag_search` tool directly with the same arguments.

### 2. Historical Root Cause Investigation (`historical_root_cause`)
**When to use:** Regression analysis or investigating previous decisions in the codebase.
1. Review recent commits: `git log --date=iso --decorate --graph --max-count 40 --oneline`
2. Ingest history into RAG using the bundled script:
   ```bash
   python .agents/skills/mcp_rag_memory_ops/git_history_ingest.py --max-commits 80 --project-id <project> --environment-id <env>
   ```
3. Search history: Use `rag_search` querying for "commit regression history blame".

### 3. Incremental Repo Sync (`refresh_repo_context`)
**When to use:** Before answering questions about frequently changing code, or when detecting outdated context.
* **Sync CLI**:
  ```bash
  python -m cerebro_python rag-sync-repos --config .agents/skills/mcp_rag_memory_ops/repos.config.json --state .gitcore/repo_context_state.json --cache-dir .cache/repo-context-repos
  ```
After syncing, run a `rag_search` normally.

### 4. Cross-Stack / Multi-Environment Investigation (`cross_stack_investigation`)
**When to use:** Explicit need to compare between stacks or environments, or analysis of cross-repo integrations.
* **CLI / MCP**: Use `rag_search` with `scope_mode` set to `custom` and explicitly defining `include_environment_ids: ["<other-env>"]`.

---

## 🧪 Testing & Evaluation Scripts

The codebase provides several diagnostic scripts in the `/scripts` directory to ensure RAG configurations are working strictly as expected:

1. **`scripts/rag_eval_levels.py`**
   - Runs a multi-level RAG evaluation. Tests cover smoke checks, isolation (ensuring strict mode doesn't leak), cross-environment queries, and temporal correctness.
   - **Usage**: `python scripts/rag_eval_levels.py --levels all`

2. **`scripts/run_rag_eval_in_docker.sh`** (and `.ps1` for Windows)
   - Performs End-to-End smoke tests directly inside the running Docker container (`mcp_rag_server`), validating database isolation in a production-like environment.

3. **`scripts/mcp_http_smoke.py`**
   - Performs a minimal HTTP smoke check to ensure the MCP JSON-RPC endpoints are responding correctly.
   - **Usage**: `python scripts/mcp_http_smoke.py --url http://localhost:8001/mcp`

---

## 🚦 Guardrails (Critical Rules)
1. **default_scope_mode_strict**: Always assume `scope-mode: strict` to avoid polluting your results with irrelevant environments.
2. **use_custom_scope_only_when_explicitly_needed**: Only broaden to `custom` when strictly required.
3. **preserve_repo_path_commit_provenance**: Preserve the exact path or commit origin when responding to the user.
4. **prefer_incremental_operations_over_full_resync**: Sync incrementally rather than indexing everything from scratch.

---

## ⚙️ Sync Configuration (repos.config.json)

The `repos.config.json` configuration file located in this directory defines what is indexed by default during repo syncing.
- **Included Extensions**: `.py`, `.js`, `.ts`, `.rs`, `.go`, `.md`, among others.
- **Default Ignored**: Hidden directories (`.git`, `.venv`), `node_modules`, `__pycache__`, build folders (`dist`, `target`), and minified files.
- **Size Limit**: 300KB per file.
