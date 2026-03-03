"""LLM Provider interface and common types."""

from __future__ import annotations
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMProvider(Protocol):
    """Common interface for all LLM providers (MiniMax, OpenRouter, DeepSeek, CLI)."""

    def score_importance(self, text: str, context: str) -> float:
        """Rate importance of a memory (0.0 - 1.0)."""
        ...

    def consolidate(self, texts: list[str]) -> str:
        """Synthesize multiple memories into a single fact."""
        ...

    def rewrite_query(self, query: str) -> str:
        """Expand search query with semantic terms."""
        ...

    def score_relevance(self, query: str, candidate_text: str) -> float:
        """Rerank candidates based on relevance (0.0 - 1.0)."""
        ...

    @property
    def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        ...
