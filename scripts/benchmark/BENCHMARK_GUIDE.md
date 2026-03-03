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
To run the benchmark against Cerebro, we use the specific adapter `scripts/cerebro_swarm_run.py` which inherits from the generic `rag_swarm_benchmark` package.

```bash
python scripts/cerebro_swarm_run.py --repo-key langchain-ai/langchain --concurrency 10
```

### What happens?
1. The **Generic Orchestrator** object spawns 10 parallel threads.
2. Each thread executes a specific, complex benchmark question about the repository against the `BaseRAGEvaluator` instance.
3. The adapter translates this to concurrent `rag-search` CLI calls.
4. The generic orchestrator tracks latency, hits, and crashes for every thread.
5. A combined `swarm_report_<timestamp>.json` is exported into `.cache/swarm-diagnostics/` showing the concurrency performance, precision@K of the chunks retrieved, and total execution wall-time.

### Using the Generic Package in other RAGs
The `rag_swarm_benchmark` folder is completely isolated from Cerebro. You can install it in other projects and orchestrate benchmarking for LangChain, LlamaIndex, or internal tools:

```python
from rag_swarm_benchmark import BaseRAGEvaluator, SwarmOrchestrator

class MyEvaluator(BaseRAGEvaluator):
    def search_rag(self, query, **kwargs):
        # Your custom DB logic
        return {"results": [...]}

    def run_agent(self, agent_id, question, target_identifier, **kwargs):
        # The logic for answering a single test
        return {"latency": 0.5, "agent_id": agent_id}

orchestrator = SwarmOrchestrator(evaluator=MyEvaluator(), concurrency=50)
orchestrator.run(["What is chunking?"], "my-target")
```

### 🤖 Jules as the LLM Judge

Once the Swarm completes its benchmark, the orchestrator **automatically** opens a GitHub issue in this repository. It tags **@jules** (Google's Agent), attaches the full JSON diagnostic report, and prompts Jules to act as the LLM Judge.

Jules will:
1. Analyze the retrieved chunks vs the expected architecture answers.
2. Review the retrieval latencies to find bottlenecks.
3. Automatically explore `cerebro_python/adapters` and open independent Pull Requests to improve the `HybridRanker` weights, `MMR` lambda values, or chunking strategies based on its analysis.

> **Note**: This requires having the GitHub CLI (`gh`) authenticated on the machine running the swarm.
