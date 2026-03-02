"""Unit tests for CognitiveService using in-memory mocks."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import pytest

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveMeta,
    CognitiveConfig,
    CognitiveScore,
    MemoryLevel,
)
from cerebro_python.application.cognitive_service import CognitiveService


# ── Lightweight mocks ────────────────────────────────────────────────────────

class _MockRepo:
    def __init__(self, chunks_by_level: dict[MemoryLevel, list[tuple[ChunkRecord, CognitiveMeta]]]) -> None:
        self._store = dict(chunks_by_level)
        self.transitions: list[tuple[str, int, MemoryLevel]] = []
        self.increments: list[tuple[str, int]] = []
        self.decayed = 0

    def get_by_level(self, level: MemoryLevel) -> list[tuple[ChunkRecord, CognitiveMeta]]:
        return self._store.get(level, [])

    def upsert_meta(self, document_id: str, chunk_index: int, meta: CognitiveMeta) -> None:
        pass

    def transition(self, document_id: str, chunk_index: int, to_level: MemoryLevel) -> bool:
        self.transitions.append((document_id, chunk_index, to_level))
        return True

    def apply_decay(self, decay_lambda: float, forget_threshold: float, now: datetime) -> int:
        self.decayed += 1
        return 2  # pretend 2 chunks forgotten

    def increment_access(self, document_id: str, chunk_index: int, now: datetime) -> None:
        self.increments.append((document_id, chunk_index))


class _AlwaysHighScorer:
    """Scorer that always returns a perfect total score."""
    def score(self, chunk: Any, query_vector: Any, now: Any, meta: Any) -> CognitiveScore:
        return CognitiveScore(recency=1.0, importance=1.0, relevance=1.0, frequency=1.0, total=1.0)


class _AlwaysLowScorer:
    """Scorer that always returns a zero total score."""
    def score(self, chunk: Any, query_vector: Any, now: Any, meta: Any) -> CognitiveScore:
        return CognitiveScore(recency=0.0, importance=0.0, relevance=0.0, frequency=0.0, total=0.0)


class _NoOpLLM:
    def score_importance(self, text: str, context: str) -> float:
        return 0.5

    def consolidate(self, texts: list[str]) -> str:
        return " | ".join(texts)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _chunk(doc_id: str = "doc1") -> ChunkRecord:
    return ChunkRecord(doc_id, 0, f"text for {doc_id}", [1.0, 0.0], {})


def _meta(level: MemoryLevel = MemoryLevel.EPISODIC) -> CognitiveMeta:
    now = datetime.now(timezone.utc).isoformat()
    return CognitiveMeta(level=level, importance=0.8, access_count=1, last_access=now, created_at=now)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestPopulateWorkingMemory:
    def test_returns_top_k_chunks(self) -> None:
        chunks = [(_chunk(f"doc{i}"), _meta()) for i in range(5)]
        repo = _MockRepo({MemoryLevel.EPISODIC: chunks, MemoryLevel.SEMANTIC: []})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(), CognitiveConfig(wm_slots=3))

        result = svc.populate_working_memory([1.0, 0.0], top_k=3)

        assert len(result) == 3

    def test_transitions_selected_to_working(self) -> None:
        chunks = [(_chunk("doc1"), _meta())]
        repo = _MockRepo({MemoryLevel.EPISODIC: chunks, MemoryLevel.SEMANTIC: []})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(), CognitiveConfig())

        svc.populate_working_memory([1.0, 0.0])

        assert any(t[2] == MemoryLevel.WORKING for t in repo.transitions)

    def test_returns_empty_when_disabled(self) -> None:
        cfg = CognitiveConfig(enabled=False)
        repo = _MockRepo({})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(), cfg)
        assert svc.populate_working_memory([1.0, 0.0]) == []


class TestPostInteractionUpdate:
    def test_increments_access_for_used_chunks(self) -> None:
        chunk = _chunk("doc1")
        repo = _MockRepo({MemoryLevel.WORKING: []})
        svc = CognitiveService(repo, _AlwaysLowScorer(), _NoOpLLM(), CognitiveConfig())

        svc.post_interaction_update([chunk], [1.0, 0.0])

        assert ("doc1", 0) in repo.increments

    def test_promotes_high_score_working_chunks(self) -> None:
        chunk = _chunk("doc1")
        meta = _meta(level=MemoryLevel.WORKING)
        repo = _MockRepo({MemoryLevel.WORKING: [(chunk, meta)]})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(), CognitiveConfig())

        promoted = svc.post_interaction_update([chunk], [1.0, 0.0])

        assert promoted >= 1
        assert any(t[2] == MemoryLevel.EPISODIC for t in repo.transitions)


class TestRunDecay:
    def test_returns_count_of_forgotten(self) -> None:
        repo = _MockRepo({})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(), CognitiveConfig())
        forgotten = svc.run_decay()
        assert forgotten == 2  # _MockRepo.apply_decay always returns 2

    def test_returns_zero_when_disabled(self) -> None:
        repo = _MockRepo({})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(), CognitiveConfig(enabled=False))
        assert svc.run_decay() == 0


class TestRunConsolidation:
    def test_no_consolidation_below_min_episodes(self) -> None:
        repo = _MockRepo({MemoryLevel.EPISODIC: [(_chunk(), _meta())]})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(),
                                CognitiveConfig(consolidation_min_episodes=3))
        assert svc.run_consolidation() == 0

    def test_creates_l3_with_enough_episodes(self) -> None:
        episodes = [(_chunk(f"ep{i}"), _meta()) for i in range(3)]
        repo = _MockRepo({MemoryLevel.EPISODIC: episodes})
        svc = CognitiveService(repo, _AlwaysHighScorer(), _NoOpLLM(),
                                CognitiveConfig(consolidation_min_episodes=3))
        created = svc.run_consolidation()
        assert created == 1
