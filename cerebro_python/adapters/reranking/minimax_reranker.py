"""MiniMax-powered reranker with heuristic fallback."""

from __future__ import annotations

import os

from cerebro_python.adapters.llm.minimax_client import MinimaxLLMClient
from cerebro_python.adapters.reranking.heuristic_reranker import HeuristicRerankerAdapter
from cerebro_python.domain.models import SearchHit


class MinimaxRerankerAdapter:
    """Rerank hits using LLM relevance scoring blended with base score."""

    def __init__(
        self,
        llm_client: MinimaxLLMClient | None = None,
        fallback: HeuristicRerankerAdapter | None = None,
        blend_weight: float | None = None,
        top_n: int | None = None,
    ) -> None:
        self._llm = llm_client or MinimaxLLMClient()
        self._fallback = fallback or HeuristicRerankerAdapter()
        self._blend_weight = float(os.getenv("RAG_LLM_RERANK_WEIGHT", "0.45")) if blend_weight is None else blend_weight
        self._blend_weight = max(0.0, min(1.0, self._blend_weight))
        self._top_n = top_n or int(os.getenv("RAG_LLM_RERANK_TOP_N", "20"))

    def rerank(self, query: str, hits: list[SearchHit], top_k: int) -> list[SearchHit]:
        if not hits:
            return []
        if not self._llm.is_available:
            return self._fallback.rerank(query=query, hits=hits, top_k=top_k)

        candidate_n = max(1, min(len(hits), self._top_n))
        rescored: list[SearchHit] = []
        for hit in hits[:candidate_n]:
            llm_score = self._llm.score_relevance(query=query, candidate_text=hit.chunk_text)
            fused = (hit.score * (1.0 - self._blend_weight)) + (llm_score * self._blend_weight)
            rescored.append(
                SearchHit(
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    chunk_text=hit.chunk_text,
                    score=fused,
                    metadata=hit.metadata,
                )
            )

        # Preserve non-reranked tail with original score so we don't drop data unexpectedly.
        tail = hits[candidate_n:]
        combined = rescored + tail
        combined.sort(key=lambda item: item.score, reverse=True)
        return combined[: max(1, top_k)]
