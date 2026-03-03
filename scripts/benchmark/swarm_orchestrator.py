"""Multi-Agent Swarm Orchestrator for RAG Benchmarking"""

import argparse
import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
EVAL_AGENT_SCRIPT = ROOT_DIR / "scripts" / "benchmark" / "eval_agent.py"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_agent(agent_id: int, repo_key: str, question: str, env_id: str, out_dir: Path) -> dict:
    """Launches an agent sub-process and waits for it to complete."""
    output_file = out_dir / f"agent_{agent_id}_result.json"

    cmd = [
        "python", str(EVAL_AGENT_SCRIPT),
        "--agent-id", str(agent_id),
        "--repo-key", repo_key,
        "--question", question,
        "--environment-id", env_id,
        "--output-file", str(output_file)
    ]

    try:
        logging.info(f"Launching Agent {agent_id} for repo: {repo_key}")
        start = time.perf_counter()
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        latency = time.perf_counter() - start

        # Parse the output
        if output_file.exists():
            with open(output_file, "r") as f:
                res = json.load(f)
                res["process_latency"] = latency
                return res
        return {"error": "output file missing", "agent_id": agent_id}
    except subprocess.CalledProcessError as e:
        logging.error(f"Agent {agent_id} crashed: {e.stderr}")
        return {"error": "crash", "stderr": e.stderr, "agent_id": agent_id}

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent RAG Orchestrator")
    parser.add_argument("--repo-key", required=True, help="Target repository key (e.g. langchain-ai/langchain)")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent agents to spawn")
    parser.add_argument("--environment-id", default="benchmark")
    args = parser.parse_args()

    # Pre-defined benchmark questions evaluating the RAG
    questions = [
        "What are the core classes used for semantic chunking?",
        "Explain the authentication mechanism implemented in this framework.",
        "How does the query rewrite adapter work?",
        "Show me the production rollback procedures.",
        "Are there any references to vector database integration?"
    ]

    out_dir = ROOT_DIR / ".cache" / "benchmark-runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_timestamp = int(time.time())

    logging.info(f"Starting swarm benchmark with {args.concurrency} agents...")
    start_time = time.perf_counter()

    results = []

    # Spawn concurrent agents
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = []
        for i in range(args.concurrency):
            # Give each agent a different question
            q = questions[i % len(questions)]
            futures.append(executor.submit(
                run_agent,
                agent_id=i,
                repo_key=args.repo_key,
                question=q,
                env_id=args.environment_id,
                out_dir=out_dir
            ))

        for future in as_completed(futures):
            res = future.result()
            results.append(res)

    total_time = time.perf_counter() - start_time

    # Generate aggregate report
    report = {
        "timestamp": run_timestamp,
        "repo": args.repo_key,
        "concurrency": args.concurrency,
        "total_wall_time_sec": round(total_time, 2),
        "agents": results
    }

    report_file = out_dir / f"swarm_report_{run_timestamp}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    logging.info(f"Swarm complete. Wall time: {round(total_time, 2)}s.")
    logging.info(f"Report written to {report_file}")

    # Invoke Jules via GitHub Issue
    try:
        issue_title = f"[Benchmark] RAG Swarm Evaluation for {args.repo_key}"
        issue_body = (
            f"## RAG Swarm Benchmark Results\n\n"
            f"- **Target Repo**: {args.repo_key}\n"
            f"- **Concurrency**: {args.concurrency} agents\n"
            f"- **Wall Time**: {round(total_time, 2)}s\n\n"
            f"### Diagnostics\n"
            f"```json\n{json.dumps(report, indent=2)}\n```\n\n"
            f"---\n"
            f"**@jules** Please act as the LLM Judge for this benchmark. Analyze the retrieved chunk IDs, the latency, and the precision. "
            f"If the retrieval quality or latency is degraded, please explore the codebase (`cerebro_python/adapters`) and propose PRs to improve "
            f"the Hybrid Ranker, MMR Lambda, or Chunking strategies."
        )

        logging.info("Creating GitHub issue to invoke Jules...")
        subprocess.run([
            "gh", "issue", "create",
            "--title", issue_title,
            "--body", issue_body,
            "--label", "benchmark,jules-review"
        ], check=True, capture_output=True)
        logging.info("Successfully handed over the evaluation to Jules via GitHub Issues!")
    except Exception as e:
        logging.warning("Failed to invoke Jules. Ensure the 'gh' CLI is authenticated and installed. " + str(e))

if __name__ == "__main__":
    main()
