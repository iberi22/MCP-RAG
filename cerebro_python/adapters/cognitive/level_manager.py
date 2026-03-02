"""Memory level manager — evaluates promotion and demotion of chunks.

Uses CognitiveScorerPort to score each chunk and compares against the
configured thresholds to decide level transitions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveConfig,
    CognitiveMeta,
    MemoryLevel,
)
from cerebro_python.domain.ports import CognitiveScorerPort, MemoryLevelPort


class DefaultLevelManager:
    """Evaluates and executes promotion/demotion transitions between memory levels."""

    def __init__(
        self,
        scorer: CognitiveScorerPort,
        repo: MemoryLevelPort,
        config: CognitiveConfig,
    ) -> None:
        self._scorer = scorer
        self._repo = repo
        self._cfg = config

    # ------------------------------------------------------------------
    def evaluate_and_promote(
        self,
        chunks_with_meta: list[tuple[ChunkRecord, CognitiveMeta]],
        query_vector: list[float],
    ) -> list[tuple[ChunkRecord, MemoryLevel]]:
        """Return (chunk, target_level) pairs for chunks that should be promoted."""
        now = datetime.now(timezone.utc)
        promotions: list[tuple[ChunkRecord, MemoryLevel]] = []
        for chunk, meta in chunks_with_meta:
            score = self._scorer.score(chunk, query_vector, now, meta)
            current = meta.level
            if score.total >= self._cfg.consolidate_threshold and current < MemoryLevel.EPISODIC:
                promotions.append((chunk, MemoryLevel.EPISODIC))
            elif score.total >= self._cfg.promote_l1_threshold and current < MemoryLevel.WORKING:
                promotions.append((chunk, MemoryLevel.WORKING))
        return promotions

    def evaluate_and_demote(
        self,
        chunks_with_meta: list[tuple[ChunkRecord, CognitiveMeta]],
        query_vector: list[float],
    ) -> list[tuple[ChunkRecord, MemoryLevel]]:
        """Return (chunk, target_level) pairs for chunks that should be demoted."""
        now = datetime.now(timezone.utc)
        demotions: list[tuple[ChunkRecord, MemoryLevel]] = []
        for chunk, meta in chunks_with_meta:
            if meta.level <= MemoryLevel.SENSORY:
                continue
            score = self._scorer.score(chunk, query_vector, now, meta)
            if score.total < self._cfg.forget_threshold:
                demotions.append((chunk, MemoryLevel(int(meta.level) - 1)))
        return demotions

    def apply_transitions(
        self, transitions: list[tuple[ChunkRecord, MemoryLevel]]
    ) -> int:
        """Execute all transitions in the repository. Returns number applied."""
        applied = 0
        for chunk, target_level in transitions:
            if self._repo.transition(chunk.document_id, chunk.chunk_index, target_level):
                applied += 1
        return applied
