"""Automated GitHub integration for LLM judging."""

import json
import logging
import subprocess
from typing import Dict, Any

def invoke_jules_judge(repo_key: str, concurrency: int, wall_time: float, report: Dict[str, Any]) -> None:
    """
    Creates a GitHub issue tagging @jules to act as an LLM judge for the benchmark results.
    Requires the 'gh' CLI to be installed and authenticated on the host machine.
    """
    try:
        issue_title = f"[Benchmark] RAG Swarm Evaluation for {repo_key}"
        issue_body = (
            f"## RAG Swarm Benchmark Results\n\n"
            f"- **Target**: {repo_key}\n"
            f"- **Concurrency**: {concurrency} parallel agents\n"
            f"- **Total Wall Time**: {round(wall_time, 2)}s\n\n"
            f"### Swarm Diagnostics\n"
            f"```json\n{json.dumps(report, indent=2)}\n```\n\n"
            f"---\n"
            f"**@jules** Please act as the LLM Judge for this benchmark. Analyze the retrieved chunks and latency. "
            f"If the retrieval quality or latency is degraded under concurrent load, "
            f"please explore the codebase and propose PRs to improve the Ranker mechanisms or Chunking strategies."
        )

        logging.info("Creating GitHub issue to hand over to Jules...")
        subprocess.run([
            "gh", "issue", "create",
            "--title", issue_title,
            "--body", issue_body,
            "--label", "benchmark,jules-review"
        ], check=True, capture_output=True)
        logging.info("Successfully requested Jules review via GitHub Issues!")
    except subprocess.CalledProcessError as e:
        logging.warning("Failed to invoke GitHub CLI. Is 'gh' installed and authenticated? " + str(e))
    except Exception as e:
        logging.warning("Unknown error creating GitHub issue: " + str(e))
