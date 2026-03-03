# Multi-Agent RAG Benchmarking (Swarm Evaluation)

Instead of traditional CI/CD pipelines which spin up a single agent, this project includes a **Machine-Level Swarm Orchestrator** to test the RAG database against heavy concurrency, large data ingestion, and actual autonomous agent reasoning.

This is critical to test Vector DB locks, connection limits, and retrieval latency (Hybrid Ranker & MMR) when multiple agents are querying the codebase simultaneously.

## 1. Seed the Community Repositories
First, we need to ingest massive repositories (like Langchain or LlamaIndex) into a fresh "benchmark" environment in the local RAG:

```bash
python scripts/benchmark/seed_community_repos.py --repos langchain-ai/langchain run-llama/llama_index
```
This script will clone the repositories into `.cache/benchmark-repos` and index everything into the vector database using the `rag-sync-repos` tool under the `benchmark` environment ID.

## 2. Launch the Swarm Orchestrator
Once indexed, launch the orchestrator to fire up multiple `eval_agent.py` instances simultaneously.

```bash
python scripts/benchmark/swarm_orchestrator.py --repo-key langchain-ai/langchain --concurrency 10
```

### What happens?
1. The orchestrator spawns 10 parallel processes (`eval_agent.py`).
2. Each agent is given a specific, complex benchmark question about the repository.
3. Every agent uses the Cerebro CLI (`rag-search`) concurrently to aggressively query the database.
4. The orchestrator tracks latency, hits, and crashes for every agent.
5. A combined `swarm_report_<timestamp>.json` is exported into `.cache/benchmark-runs/` showing the concurrency performance, precision@K of the chunks retrieved, and total execution wall-time.

### 🤖 Jules as the LLM Judge

Once the Swarm completes its benchmark, the orchestrator **automatically** opens a GitHub issue in this repository. It tags **@jules** (Google's Agent), attaches the full JSON diagnostic report, and prompts Jules to act as the LLM Judge.

Jules will:
1. Analyze the retrieved chunks vs the expected architecture answers.
2. Review the retrieval latencies to find bottlenecks.
3. Automatically explore `cerebro_python/adapters` and open independent Pull Requests to improve the `HybridRanker` weights, `MMR` lambda values, or chunking strategies based on its analysis.

> **Note**: This requires having the GitHub CLI (`gh`) authenticated on the machine running the swarm.
