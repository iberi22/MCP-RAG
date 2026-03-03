"""Cerebro Protocol RAG Swarm Orchestrator

This script wraps the Cerebro CLI using the generic `rag_swarm_benchmark`
package to evaluate our specific database and memory policy logic.
"""
# ruff: noqa: E402

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rag_swarm_benchmark import BaseRAGEvaluator, SwarmOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class CerebroRAGEvaluator(BaseRAGEvaluator):
    """Adapter to let the Swarm framework talk to Cerebro RAG via Python Subprocess"""

    def search_rag(self, query: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """Executes a strict search query against the local Cerebro RAG system."""
        project_id = kwargs.get("project_id", "community-benchmarks")
        env_id = kwargs.get("environment_id", "benchmark")

        cmd = [
            "python", "-m", "cerebro_python", "rag-search",
            "--query", query,
            "--top-k", str(top_k),
            "--project-id", project_id,
            "--environment-id", env_id,
            "--scope-mode", "strict"
        ]

        try:
            res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, check=True)
            return json.loads(res.stdout)
        except Exception as e:
            return {"error": str(e), "results": []}

    def run_agent(self, agent_id: int, question: str, target_identifier: str, **kwargs) -> Dict[str, Any]:
        """The entrypoint for the Orchestrator to trigger an autonomous evaluation."""
        logging.info(f"[Agent {agent_id}] Evaluating query against {target_identifier}")

        search_data = self.search_rag(query=question, **kwargs)

        retrieved_chunks = []
        chunk_ids = []

        if "results" in search_data:
            for item in search_data["results"]:
                meta = item.get("metadata", {})
                if meta.get("repo_key") == target_identifier or target_identifier in meta.get("repo_url", ""):
                    retrieved_chunks.append({
                        "chunk_id": item.get("chunk_id"),
                        "score": item.get("score"),
                        "text_preview": item.get("text", "")[:100]
                    })
                    chunk_ids.append(item.get("chunk_id"))

        return {
            "agent_id": agent_id,
            "question": question,
            "target": target_identifier,
            "total_hits": len(search_data.get("results", [])),
            "filtered_hits": len(retrieved_chunks),
            "retrieved_chunk_ids": chunk_ids,
            "chunks": retrieved_chunks
        }


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Cerebro Swarm Orchestrator")
    parser.add_argument("--repo-key", required=True, help="Target repository key (e.g. langchain-ai/langchain)")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent agents to spawn")
    parser.add_argument("--environment-id", default="benchmark")
    parser.add_argument("--skip-jules", action="store_true", help="Do not trigger the GitHub `@jules` issue")
    args = parser.parse_args()

    # Domain specific evaluation questions
    questions = [
        "What are the core classes used for semantic chunking?",
        "Explain the authentication mechanism implemented in this framework.",
        "How does the query rewrite adapter work?",
        "Show me the production rollback procedures.",
        "Are there any references to vector database integration?"
    ]

    evaluator = CerebroRAGEvaluator()
    orchestrator = SwarmOrchestrator(
        evaluator=evaluator,
        concurrency=args.concurrency,
        out_dir=str(ROOT_DIR / ".cache" / "swarm-diagnostics")
    )

    orchestrator.run(
        questions=questions,
        target_identifier=args.repo_key,
        invoke_jules=not args.skip_jules,
        environment_id=args.environment_id
    )

if __name__ == "__main__":
    main()
