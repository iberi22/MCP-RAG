"""Domain ports (hexagonal interfaces)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveMeta,
    CognitiveScore,
    MemoryLevel,
    SearchHit,
    StorageStats,
)


class EmbeddingPort(Protocol):
    def embed(self, text: str) -> list[float]: ...


class ChunkingPort(Protocol):
    def split(self, text: str) -> list[str]: ...


class MemoryRepositoryPort(Protocol):
    def replace_document(self, document_id: str, records: list[ChunkRecord]) -> int: ...
    def fetch_all_chunks(self) -> list[ChunkRecord]: ...
    def delete_document(self, document_id: str) -> int: ...
    def stats(self) -> StorageStats: ...


class RankerPort(Protocol):
    def rank(self, query: str, query_vector: list[float], chunks: list[ChunkRecord], top_k: int) -> list[SearchHit]: ...


class MemoryPolicyPort(Protocol):
    def sanitize_records(self, records: list[ChunkRecord]) -> list[ChunkRecord]: ...


class RerankerPort(Protocol):
    def rerank(self, query: str, hits: list[SearchHit], top_k: int) -> list[SearchHit]: ...


class QueryRewritePort(Protocol):
    def rewrite(self, query: str) -> str: ...


class ScopeStrategyPort(Protocol):
    def select_additional_environments(
        self,
        query: str,
        environment_id: str | None,
        requested_environment_ids: list[str] | None,
        scope_mode: str,
    ) -> list[str]: ...


# ── Cognitive Memory Ports ─────────────────────────────────────────────────────

class CognitiveScorerPort(Protocol):
    """Scores a chunk against a query vector using recency, importance, relevance, frequency."""
    def score(
        self,
        chunk: ChunkRecord,
        query_vector: list[float],
        now: datetime,
        meta: CognitiveMeta,
    ) -> CognitiveScore: ...


class MemoryLevelPort(Protocol):
    """Storage operations scoped to memory levels."""
    def get_by_level(self, level: MemoryLevel) -> list[tuple[ChunkRecord, CognitiveMeta]]: ...
    def upsert_meta(self, document_id: str, chunk_index: int, meta: CognitiveMeta) -> None: ...
    def transition(self, document_id: str, chunk_index: int, to_level: MemoryLevel) -> bool: ...
    def apply_decay(self, decay_lambda: float, forget_threshold: float, now: datetime) -> int: ...
    def increment_access(self, document_id: str, chunk_index: int, now: datetime) -> None: ...


class LLMScorerPort(Protocol):
    """LLM-powered importance scoring and episodic consolidation."""
    def score_importance(self, text: str, context: str) -> float: ...
    def consolidate(self, texts: list[str]) -> str: ...

