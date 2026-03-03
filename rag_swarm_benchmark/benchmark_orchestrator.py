"""The generic Swarm Benchmarking Orchestrator."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Type

from .base_evaluator import BaseRAGEvaluator
from .github_judge import invoke_jules_judge

class SwarmOrchestrator:
    """
    Executes concurrent calls against a `BaseRAGEvaluator` instance
    and collates the results into a swarm benchmark report.
    """

    def __init__(self, evaluator: BaseRAGEvaluator, concurrency: int = 5, out_dir: str = ".cache/benchmark-runs"):
        self.evaluator = evaluator
        self.concurrency = concurrency
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def run(self, questions: List[str], target_identifier: str, invoke_jules: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Runs the benchmark swarm.

        Args:
            questions (List[str]): Scenarios/prompts to ask the RAG system.
            target_identifier (str): Repo namespace or ID.
            invoke_jules (bool): Whether to auto-open a GitHub issue tagging @jules.
            **kwargs: Passed downwards to the evaluator.
        """
        logging.info(f"Starting Swarm Benchmark with {self.concurrency} concurrent agents targeting '{target_identifier}'...")
        start_time = time.perf_counter()
        results = []
        run_timestamp = int(time.time())

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = []
            for i in range(self.concurrency):
                q = questions[i % len(questions)]
                futures.append(executor.submit(
                    self._wrapped_agent_run,
                    agent_id=i,
                    question=q,
                    target=target_identifier,
                    **kwargs
                ))

            for future in as_completed(futures):
                res = future.result()
                results.append(res)

        total_time = time.perf_counter() - start_time
        logging.info(f"Swarm complete. Total wall time: {round(total_time, 2)}s.")

        report = {
            "timestamp": run_timestamp,
            "target": target_identifier,
            "concurrency": self.concurrency,
            "total_wall_time_sec": round(total_time, 2),
            "agents": results
        }

        report_file = self.out_dir / f"swarm_report_{run_timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logging.info(f"Report written to {report_file}")

        if invoke_jules:
            invoke_jules_judge(
                repo_key=target_identifier,
                concurrency=self.concurrency,
                wall_time=total_time,
                report=report
            )

        return report

    def _wrapped_agent_run(self, agent_id: int, question: str, target: str, **kwargs) -> Dict[str, Any]:
        """Wraps the evaluator method to safely catch exceptions and track precise latency."""
        try:
            start = time.perf_counter()
            res = self.evaluator.run_agent(agent_id=agent_id, question=question, target_identifier=target, **kwargs)
            res["process_latency_sec"] = round(time.perf_counter() - start, 3)
            return res
        except Exception as e:
            logging.error(f"Agent {agent_id} failed: {e}")
            return {"error": str(e), "agent_id": agent_id}
