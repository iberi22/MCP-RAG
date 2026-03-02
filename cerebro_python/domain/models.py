"""Domain models."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


@dataclass(slots=True, frozen=True)
class ChunkRecord:
    document_id: str
    chunk_index: int
    chunk_text: str
    embedding: list[float]
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class SearchHit:
    document_id: str
    chunk_index: int
    chunk_text: str
    score: float
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StorageStats:
    storage: str
    documents: int
    chunks: int
    details: dict[str, Any]


# ── Cognitive Memory System ───────────────────────────────────────────────────

class MemoryLevel(IntEnum):
    """Hierarchical memory level (higher = more consolidated)."""
    SENSORY = 0   # L0: raw session buffer, no embedding required
    WORKING = 1   # L1: active context for current task
    EPISODIC = 2  # L2: persisted events with Ebbinghaus decay
    SEMANTIC = 3  # L3: distilled facts, LLM-synthesised, permanent


@dataclass(slots=True)
class CognitiveMeta:
    """Cognitive metadata attached to each chunk record."""
    level: MemoryLevel = MemoryLevel.SENSORY
    importance: float = 0.5          # 0-1, assigned by LLM (or default 0.5)
    access_count: int = 0            # how many times this chunk was retrieved
    last_access: str = ""           # ISO 8601 datetime string
    created_at: str = ""            # ISO 8601 datetime string
    source_ids: list[str] = field(default_factory=list)  # provenance for L3


@dataclass(slots=True, frozen=True)
class CognitiveScore:
    """Multi-factor relevance score for a memory chunk."""
    recency: float
    importance: float
    relevance: float
    frequency: float
    total: float


@dataclass(slots=True)
class CognitiveConfig:
    """Runtime configuration for the cognitive memory system."""
    enabled: bool = True
    wm_slots: int = 20
    promote_l1_threshold: float = 0.6
    consolidate_threshold: float = 0.75
    forget_threshold: float = 0.15
    decay_lambda: float = 0.02
    recency_weight: float = 0.25
    importance_weight: float = 0.30
    relevance_weight: float = 0.35
    frequency_weight: float = 0.10
    consolidation_min_episodes: int = 3
    decay_interval_hours: int = 24

    @classmethod
    def from_env(cls) -> "CognitiveConfig":
        """Build config from RAG_COGNITIVE_* environment variables."""
        return cls(
            enabled=os.getenv("RAG_COGNITIVE_ENABLED", "true").lower() == "true",
            wm_slots=int(os.getenv("RAG_COGNITIVE_WM_SLOTS", "20")),
            promote_l1_threshold=float(os.getenv("RAG_COGNITIVE_PROMOTE_L1_THRESHOLD", "0.6")),
            consolidate_threshold=float(os.getenv("RAG_COGNITIVE_CONSOLIDATE_THRESHOLD", "0.75")),
            forget_threshold=float(os.getenv("RAG_COGNITIVE_FORGET_THRESHOLD", "0.15")),
            decay_lambda=float(os.getenv("RAG_COGNITIVE_DECAY_LAMBDA", "0.02")),
            recency_weight=float(os.getenv("RAG_COGNITIVE_RECENCY_WEIGHT", "0.25")),
            importance_weight=float(os.getenv("RAG_COGNITIVE_IMPORTANCE_WEIGHT", "0.30")),
            relevance_weight=float(os.getenv("RAG_COGNITIVE_RELEVANCE_WEIGHT", "0.35")),
            frequency_weight=float(os.getenv("RAG_COGNITIVE_FREQUENCY_WEIGHT", "0.10")),
            consolidation_min_episodes=int(os.getenv("RAG_COGNITIVE_CONSOLIDATION_MIN_EPISODES", "3")),
            decay_interval_hours=int(os.getenv("RAG_COGNITIVE_DECAY_INTERVAL_HOURS", "24")),
        )
