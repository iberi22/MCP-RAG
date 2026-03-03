"""Generic RAG Swarm Benchmark Package

This package allows evaluating any Retrieval-Augmented Generation (RAG) system
by orchestrating a massive parallel swarm of queries and feeding the
results to a GitHub-native LLM Judge (like @jules) for architecture reviews.
"""

from .base_evaluator import BaseRAGEvaluator
from .benchmark_orchestrator import SwarmOrchestrator
from .github_judge import invoke_jules_judge

__all__ = [
    "BaseRAGEvaluator",
    "SwarmOrchestrator",
    "invoke_jules_judge"
]
