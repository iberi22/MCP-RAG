"""Multi-Agent Swarm Evaluator Agent

This script is spawned by the swarm orchestrator. It represents a single
autonomous agent attempting to answer a prompt using the Cerebro RAG system.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

def run_rag_search(query: str, project_id: str, environment_id: str) -> dict:
    """Executes a strict search query against the RAG system."""
    cmd = [
        "python", "-m", "cerebro_python", "rag-search",
        "--query", query,
        "--top-k", "5",
        "--project-id", project_id,
        "--environment-id", environment_id,
        "--scope-mode", "strict"
    ]
    try:
        res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as e:
        return {"error": str(e), "results": []}

def main():
    parser = argparse.ArgumentParser(description="Single benchmark evaluator agent.")
    parser.add_argument("--agent-id", required=True, help="Unique identifier for this agent")
    parser.add_argument("--repo-key", required=True, help="Target repository key in RAG")
    parser.add_argument("--question", required=True, help="The benchmark question to answer")
    parser.add_argument("--environment-id", default="benchmark")
    parser.add_argument("--output-file", required=True, help="Path to write the agent JSON result")
    args = parser.parse_args()

    print(f"[Agent {args.agent_id}] Starting evaluation for {args.repo_key}...")
    start_time = time.perf_counter()

    # Step 1: Execute RAG plan/search
    # For a true autonomous agent, we would loop over Minimax LLM here.
    # For benchmarking retrieval reliability under concurrency, we will perform
    # direct search operations.
    search_data = run_rag_search(
        query=args.question,
        project_id="community-benchmarks",
        environment_id=args.environment_id
    )

    retrieved_chunks = []
    chunk_ids = []
    if "results" in search_data:
        for item in search_data["results"]:
            meta = item.get("metadata", {})
            # Filter logically by repo_key if needed, though project_id limits it somewhat
            if meta.get("repo_key") == args.repo_key or args.repo_key in meta.get("repo_url", ""):
                 retrieved_chunks.append({
                     "chunk_id": item.get("chunk_id"),
                     "score": item.get("score"),
                     "text_preview": item.get("text", "")[:100]
                 })
                 chunk_ids.append(item.get("chunk_id"))

    end_time = time.perf_counter()

    # Create the result payload
    result = {
        "agent_id": args.agent_id,
        "repo_key": args.repo_key,
        "question": args.question,
        "latency_sec": round(end_time - start_time, 3),
        "total_hits": len(search_data.get("results", [])),
        "filtered_hits": len(retrieved_chunks),
        "retrieved_chunk_ids": chunk_ids,
        "chunks": retrieved_chunks
    }

    # Write output for orchestrator
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[Agent {args.agent_id}] Finished in {result['latency_sec']}s")

if __name__ == "__main__":
    main()
