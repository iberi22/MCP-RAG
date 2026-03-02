"""CognitiveService — application-layer orchestrator for the cognitive memory system.

Coordinates all cognitive adapters (scorer, level manager, decay engine,
consolidator) to provide a high-level API for:

  - populate_working_memory : load top-K relevant chunks into L1
  - post_interaction_update : promote frequently-accessed chunks
  - run_decay              : apply Ebbinghaus forgetting to L2
  - run_consolidation      : synthesise L2 clusters into L3 facts
"""

from __future__ import annotations

from datetime import datetime, timezone

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveConfig,
    CognitiveMeta,
    MemoryLevel,
)
from cerebro_python.domain.ports import (
    CognitiveScorerPort,
    LLMScorerPort,
    MemoryLevelPort,
)


class CognitiveService:
    """High-level cognitive memory orchestrator."""

    def __init__(
        self,
        level_repo: MemoryLevelPort,
        scorer: CognitiveScorerPort,
        llm: LLMScorerPort,
        config: CognitiveConfig,
    ) -> None:
        self._repo = level_repo
        self._scorer = scorer
        self._llm = llm
        self._cfg = config

    # ------------------------------------------------------------------
    def populate_working_memory(
        self,
        query_vector: list[float],
        top_k: int | None = None,
    ) -> list[ChunkRecord]:
        """Pull top-K chunks from L2+L3 by cognitive score → promote to L1.

        Returns the selected chunks ordered by descending cognitive score.
        """
        if not self._cfg.enabled:
            return []

        top_k = top_k or self._cfg.wm_slots
        now = datetime.now(timezone.utc)

        # Gather candidates from episodic and semantic memory
        candidates: list[tuple[ChunkRecord, CognitiveMeta, float]] = []
        for level in (MemoryLevel.EPISODIC, MemoryLevel.SEMANTIC):
            for chunk, meta in self._repo.get_by_level(level):
                score = self._scorer.score(chunk, query_vector, now, meta)
                candidates.append((chunk, meta, score.total))

        candidates.sort(key=lambda t: t[2], reverse=True)
        selected = candidates[:top_k]

        # Mark selected chunks as WORKING level
        for chunk, _, _ in selected:
            self._repo.transition(chunk.document_id, chunk.chunk_index, MemoryLevel.WORKING)

        return [chunk for chunk, _, _ in selected]

    def post_interaction_update(
        self,
        used_chunks: list[ChunkRecord],
        query_vector: list[float],
    ) -> int:
        """After a search: increment access counts and evaluate promotions.

        Returns the number of chunks promoted to EPISODIC (L2).
        """
        if not self._cfg.enabled:
            return 0

        now = datetime.now(timezone.utc)
        for chunk in used_chunks:
            self._repo.increment_access(chunk.document_id, chunk.chunk_index, now)

        # Re-evaluate current L1 chunks for further promotion to L2
        working = self._repo.get_by_level(MemoryLevel.WORKING)
        promoted = 0
        for chunk, meta in working:
            score = self._scorer.score(chunk, query_vector, now, meta)
            if score.total >= self._cfg.consolidate_threshold:
                if self._repo.transition(chunk.document_id, chunk.chunk_index, MemoryLevel.EPISODIC):
                    promoted += 1
        return promoted

    def run_decay(self) -> int:
        """Apply Ebbinghaus decay to L2 memories. Returns chunks forgotten."""
        if not self._cfg.enabled:
            return 0
        return self._repo.apply_decay(
            decay_lambda=self._cfg.decay_lambda,
            forget_threshold=self._cfg.forget_threshold,
            now=datetime.now(timezone.utc),
        )

    def run_consolidation(self) -> int:
        """Synthesise L2 episode clusters into L3 semantic facts.

        Returns the number of new L3 facts created.
        """
        if not self._cfg.enabled:
            return 0

        episodes = self._repo.get_by_level(MemoryLevel.EPISODIC)
        if len(episodes) < self._cfg.consolidation_min_episodes:
            return 0

        # Sort by importance desc, take first cluster
        episodes.sort(key=lambda pair: pair[1].importance, reverse=True)
        cluster = episodes[: self._cfg.consolidation_min_episodes]
        texts = [chunk.chunk_text for chunk, _ in cluster]
        synthesized = self._llm.consolidate(texts)

        # Store synthesised fact with provenance
        import uuid
        synthetic_doc_id = f"L3-{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(timezone.utc).isoformat()
        source_ids = [chunk.document_id for chunk, _ in cluster]

        self._repo.upsert_meta(
            document_id=synthetic_doc_id,
            chunk_index=0,
            meta=CognitiveMeta(
                level=MemoryLevel.SEMANTIC,
                importance=1.0,
                access_count=0,
                last_access=now_str,
                created_at=now_str,
                source_ids=source_ids,
            ),
        )
        return 1

    def score_importance_with_llm(self, text: str, context: str) -> float:
        """Quick helper to get LLM importance score for a single text."""
        return self._llm.score_importance(text, context)
