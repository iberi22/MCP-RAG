"""Local cognitive scorer — pure math, no LLM required.

Implements CognitiveScorerPort using a weighted combination of:
  - Recency   : exponential decay since last access
  - Importance: LLM-assigned score (or neutral 0.5 default)
  - Relevance : cosine similarity between query and chunk embedding
  - Frequency : log-normalised access count
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveConfig,
    CognitiveMeta,
    CognitiveScore,
)


class LocalCognitiveScorer:
    """Scores chunks for cognitive memory promotion/demotion without LLM calls."""

    def __init__(self, config: CognitiveConfig) -> None:
        self._cfg = config

    # ------------------------------------------------------------------
    def score(
        self,
        chunk: ChunkRecord,
        query_vector: list[float],
        now: datetime,
        meta: CognitiveMeta,
    ) -> CognitiveScore:
        recency = self._recency(meta, now)
        relevance = self._cosine(chunk.embedding, query_vector)
        frequency = self._frequency(meta.access_count)

        total = (
            self._cfg.recency_weight * recency
            + self._cfg.importance_weight * meta.importance
            + self._cfg.relevance_weight * relevance
            + self._cfg.frequency_weight * frequency
        )
        return CognitiveScore(
            recency=recency,
            importance=meta.importance,
            relevance=relevance,
            frequency=frequency,
            total=min(1.0, max(0.0, total)),
        )

    # ------------------------------------------------------------------
    def _recency(self, meta: CognitiveMeta, now: datetime) -> float:
        if not meta.last_access:
            return 1.0  # brand-new chunk — treat as fully recent
        try:
            last = datetime.fromisoformat(meta.last_access)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except ValueError:
            return 0.5
        elapsed_hours = max(0.0, (now - last).total_seconds() / 3600.0)
        return math.exp(-self._cfg.decay_lambda * elapsed_hours)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1e-9
        norm_b = math.sqrt(sum(x * x for x in b)) or 1e-9
        return max(-1.0, min(1.0, dot / (norm_a * norm_b)))

    @staticmethod
    def _frequency(access_count: int) -> float:
        return math.log(1 + access_count) / math.log(2 + access_count)
