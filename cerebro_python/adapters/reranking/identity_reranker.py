"""No-op reranker adapter."""

from __future__ import annotations

from cerebro_python.domain.models import SearchHit


class IdentityRerankerAdapter:
    def rerank(self, query: str, hits: list[SearchHit], top_k: int) -> list[SearchHit]:
        return hits[: max(1, top_k)]

