"""Base Evaluator for the Generic RAG Swarm Benchmark.

Inherit from this class to integrate any RAG system (LangChain, LlamaIndex, Cerebro, etc.)
with the swarm benchmarking orchestrator.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseRAGEvaluator(ABC):
    """Abstract base class for integrating a custom RAG implementation."""

    @abstractmethod
    def search_rag(self, query: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """
        Executes a retrieval operation against the RAG system.

        Args:
            query (str): The search query or benchmark question.
            top_k (int): Number of chunks to retrieve.
            **kwargs: Additional engine-specific arguments (e.g., project_id, environment_id).

        Returns:
            Dict[str, Any]: A generic dictionary containing at minimum:
                - `chunks`: A list of dictionaries with `chunk_id` and `text_preview`.
                - `total_hits`: Integer representing the number of matches found.
        """
        pass

    @abstractmethod
    def run_agent(self, agent_id: int, question: str, target_identifier: str, **kwargs) -> Dict[str, Any]:
        """
        The entrypoint for the Orchestrator to trigger an autonomous evaluation.
        Often this wraps `search_rag` or involves a multi-step chain.

        Args:
            agent_id (int): ID assigned to the swarm agent.
            question (str): The benchmark scenario prompt.
            target_identifier (str): Repo key, document ID, or namespace to filter the RAG.
            **kwargs: Implementation-specific args.

        Returns:
            Dict[str, Any]: A result dictionary that will be sent to the HTML/JSON report.
        """
        pass
