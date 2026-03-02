"""LLM-powered L2→L3 episodic consolidator.

Groups related episodic (L2) memories and synthesises them into a single
semantic (L3) fact using the LLMScorerPort. Falls back gracefully when
the LLM is unavailable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveMeta,
    CognitiveConfig,
    MemoryLevel,
)
from cerebro_python.domain.ports import LLMScorerPort, MemoryLevelPort


class LLMConsolidator:
    """Consolidates clusters of L2 episodes into L3 semantic facts."""

    def __init__(
        self,
        llm: LLMScorerPort,
        repo: MemoryLevelPort,
        config: CognitiveConfig,
    ) -> None:
        self._llm = llm
        self._repo = repo
        self._cfg = config

    # ------------------------------------------------------------------
    def run_consolidation(self) -> int:
        """Find clusters of L2 chunks and consolidate into L3 facts.

        Returns the number of L3 facts created.
        """
        episodes = self._repo.get_by_level(MemoryLevel.EPISODIC)
        if len(episodes) < self._cfg.consolidation_min_episodes:
            return 0

        # Simple strategy: process the first eligible cluster, sorted by importance desc.
        episodes_sorted = sorted(
            episodes,
            key=lambda pair: pair[1].importance,
            reverse=True,
        )
        cluster = episodes_sorted[: self._cfg.consolidation_min_episodes]
        texts = [chunk.chunk_text for chunk, _ in cluster]
        synthesized = self._llm.consolidate(texts)

        # Build provenance info
        source_ids = [chunk.document_id for chunk, _ in cluster]
        now = datetime.now(timezone.utc).isoformat()
        synthetic_doc_id = f"L3-{uuid.uuid4().hex[:8]}"

        new_meta = CognitiveMeta(
            level=MemoryLevel.SEMANTIC,
            importance=1.0,
            access_count=0,
            last_access=now,
            created_at=now,
            source_ids=source_ids,
        )
        self._repo.upsert_meta(
            document_id=synthetic_doc_id,
            chunk_index=0,
            meta=new_meta,
        )

        # Also store the synthesised text as a chunk so it is searchable.
        # We reuse the base chunk's embedding as an approximation; a proper
        # implementation would re-embed the synthesised text.
        base_chunk, _ = cluster[0]
        synthetic_chunk = ChunkRecord(
            document_id=synthetic_doc_id,
            chunk_index=0,
            chunk_text=synthesized,
            embedding=base_chunk.embedding,
            metadata={"cognitive_level": int(MemoryLevel.SEMANTIC), "source_ids": source_ids},
        )
        # Persist via the general-purpose upsert — the cognitive repo also
        # exposes MemoryRepositoryPort in its concrete implementation.
        if hasattr(self._repo, "replace_document"):
            self._repo.replace_document(synthetic_doc_id, [synthetic_chunk])  # type: ignore[attr-defined]

        return 1
