"""Unit tests for LocalCognitiveScorer."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveMeta,
    CognitiveConfig,
    MemoryLevel,
)
from cerebro_python.adapters.cognitive.memory_scorer import LocalCognitiveScorer


def _chunk(embedding: list[float]) -> ChunkRecord:
    return ChunkRecord("doc1", 0, "test memory text", embedding, {})


def _meta(
    access_count: int = 0,
    last_access: datetime | None = None,
    importance: float = 0.5,
    level: MemoryLevel = MemoryLevel.WORKING,
) -> CognitiveMeta:
    la = (last_access or datetime.now(timezone.utc)).isoformat()
    return CognitiveMeta(
        level=level,
        importance=importance,
        access_count=access_count,
        last_access=la,
        created_at=la,
    )


@pytest.fixture
def scorer() -> LocalCognitiveScorer:
    return LocalCognitiveScorer(CognitiveConfig())


def test_recency_decays_with_time(scorer: LocalCognitiveScorer) -> None:
    now = datetime.now(timezone.utc)
    chunk = _chunk([1.0, 0.0])
    query = [1.0, 0.0]

    recent_score = scorer.score(chunk, query, now, _meta(last_access=now)).recency
    old_score = scorer.score(
        chunk, query, now,
        _meta(last_access=now - timedelta(hours=100))
    ).recency

    assert recent_score > old_score
    assert 0.0 <= old_score <= 1.0
    assert 0.0 <= recent_score <= 1.0


def test_relevance_higher_for_aligned_vectors(scorer: LocalCognitiveScorer) -> None:
    now = datetime.now(timezone.utc)
    meta = _meta()

    aligned = scorer.score(_chunk([1.0, 0.0]), [1.0, 0.0], now, meta).relevance
    orthogonal = scorer.score(_chunk([0.0, 1.0]), [1.0, 0.0], now, meta).relevance

    assert aligned > orthogonal
    assert aligned > 0.9  # nearly 1.0


def test_high_importance_boosts_total(scorer: LocalCognitiveScorer) -> None:
    now = datetime.now(timezone.utc)
    chunk = _chunk([1.0, 0.0])
    query = [1.0, 0.0]

    low = scorer.score(chunk, query, now, _meta(importance=0.1)).total
    high = scorer.score(chunk, query, now, _meta(importance=0.9)).total

    assert high > low


def test_frequency_increases_with_access_count(scorer: LocalCognitiveScorer) -> None:
    now = datetime.now(timezone.utc)
    chunk = _chunk([1.0, 0.0])
    query = [1.0, 0.0]

    s0 = scorer.score(chunk, query, now, _meta(access_count=0)).frequency
    s10 = scorer.score(chunk, query, now, _meta(access_count=10)).frequency

    assert s10 > s0


def test_total_score_bounded(scorer: LocalCognitiveScorer) -> None:
    now = datetime.now(timezone.utc)
    chunk = _chunk([1.0, 0.0])
    query = [1.0, 0.0]
    meta = _meta(access_count=100, importance=1.0)

    result = scorer.score(chunk, query, now, meta)

    assert 0.0 <= result.total <= 1.0


def test_empty_embedding_returns_zero_relevance(scorer: LocalCognitiveScorer) -> None:
    now = datetime.now(timezone.utc)
    result = scorer.score(_chunk([]), [1.0, 0.0], now, _meta())
    assert result.relevance == 0.0
