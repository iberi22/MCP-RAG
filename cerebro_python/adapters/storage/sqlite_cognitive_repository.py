"""SQLite-backed cognitive repository — implements MemoryLevelPort.

Manages the ``cognitive_meta`` table which tracks level, importance,
access counts and decay metadata for every chunk in ``rag_chunks``.
The existing ``rag_chunks`` table is NOT modified.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cerebro_python.domain.models import (
    ChunkRecord,
    CognitiveMeta,
    MemoryLevel,
)


class SqliteCognitiveRepository:
    """Persists cognitive metadata alongside the existing RAG chunk store."""

    def __init__(self, db_path: str = "cerebro_rag.db") -> None:
        self._db_path = db_path
        self._ensure_schema()

    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        Path(self._db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cognitive_meta (
                    document_id   TEXT NOT NULL,
                    chunk_index   INTEGER NOT NULL,
                    level         INTEGER NOT NULL DEFAULT 0,
                    importance    REAL    NOT NULL DEFAULT 0.5,
                    access_count  INTEGER NOT NULL DEFAULT 0,
                    last_access   TEXT    NOT NULL DEFAULT (datetime('now')),
                    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                    source_ids    TEXT    NOT NULL DEFAULT '[]',
                    PRIMARY KEY (document_id, chunk_index)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cognitive_level "
                "ON cognitive_meta(level)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cognitive_decay "
                "ON cognitive_meta(level, last_access)"
            )

    # ------------------------------------------------------------------
    def get_by_level(
        self, level: MemoryLevel
    ) -> list[tuple[ChunkRecord, CognitiveMeta]]:
        """Return all chunks at a given memory level with their cognitive meta."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.document_id, r.chunk_index, r.chunk_text, r.embedding, r.metadata,
                       m.level, m.importance, m.access_count, m.last_access, m.created_at, m.source_ids
                FROM   rag_chunks r
                JOIN   cognitive_meta m
                       ON r.document_id = m.document_id AND r.chunk_index = m.chunk_index
                WHERE  m.level = ?
                """,
                (int(level),),
            ).fetchall()
        result: list[tuple[ChunkRecord, CognitiveMeta]] = []
        for row in rows:
            chunk = ChunkRecord(
                document_id=row["document_id"],
                chunk_index=int(row["chunk_index"]),
                chunk_text=row["chunk_text"],
                embedding=[float(x) for x in json.loads(row["embedding"])],
                metadata=json.loads(row["metadata"]),
            )
            meta = CognitiveMeta(
                level=MemoryLevel(int(row["level"])),
                importance=float(row["importance"]),
                access_count=int(row["access_count"]),
                last_access=row["last_access"] or "",
                created_at=row["created_at"] or "",
                source_ids=json.loads(row["source_ids"]),
            )
            result.append((chunk, meta))
        return result

    def upsert_meta(
        self, document_id: str, chunk_index: int, meta: CognitiveMeta
    ) -> None:
        """Insert or replace cognitive metadata for a chunk."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cognitive_meta
                    (document_id, chunk_index, level, importance, access_count,
                     last_access, created_at, source_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id, chunk_index) DO UPDATE SET
                    level        = excluded.level,
                    importance   = excluded.importance,
                    access_count = excluded.access_count,
                    last_access  = excluded.last_access,
                    source_ids   = excluded.source_ids
                """,
                (
                    document_id,
                    chunk_index,
                    int(meta.level),
                    meta.importance,
                    meta.access_count,
                    meta.last_access or datetime.now(timezone.utc).isoformat(),
                    meta.created_at or datetime.now(timezone.utc).isoformat(),
                    json.dumps(meta.source_ids),
                ),
            )

    def transition(
        self, document_id: str, chunk_index: int, to_level: MemoryLevel
    ) -> bool:
        """Move a chunk to a new memory level. Returns True if the row existed."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE cognitive_meta SET level = ?, last_access = ? "
                "WHERE document_id = ? AND chunk_index = ?",
                (
                    int(to_level),
                    datetime.now(timezone.utc).isoformat(),
                    document_id,
                    chunk_index,
                ),
            )
        return cursor.rowcount > 0

    def apply_decay(
        self,
        decay_lambda: float,
        forget_threshold: float,
        now: datetime,
    ) -> int:
        """Apply Ebbinghaus decay to L2 (EPISODIC) memories.

        Computes ``strength = exp(-lambda * elapsed_hours)`` for each L2 chunk.
        Chunks whose strength falls below ``forget_threshold`` are removed.
        Returns the count of forgotten chunks.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT document_id, chunk_index, last_access "
                "FROM cognitive_meta WHERE level = ?",
                (int(MemoryLevel.EPISODIC),),
            ).fetchall()

            to_delete: list[tuple[str, int]] = []
            for row in rows:
                try:
                    last = datetime.fromisoformat(row["last_access"])
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    last = now  # can't parse — treat as brand new

                elapsed_hours = max(0.0, (now - last).total_seconds() / 3600.0)
                strength = math.exp(-decay_lambda * elapsed_hours)
                if strength < forget_threshold:
                    to_delete.append((row["document_id"], row["chunk_index"]))

            for doc_id, chunk_idx in to_delete:
                conn.execute(
                    "DELETE FROM cognitive_meta WHERE document_id = ? AND chunk_index = ?",
                    (doc_id, chunk_idx),
                )
        return len(to_delete)

    def increment_access(
        self, document_id: str, chunk_index: int, now: datetime
    ) -> None:
        """Increment access count and update last_access timestamp."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE cognitive_meta
                SET access_count = access_count + 1,
                    last_access  = ?
                WHERE document_id = ? AND chunk_index = ?
                """,
                (now.isoformat(), document_id, chunk_index),
            )

    # ------------------------------------------------------------------
    def init_chunk(self, document_id: str, chunk_index: int) -> None:
        """Ensure a chunk has a cognitive_meta row (L0/SENSORY by default)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO cognitive_meta
                    (document_id, chunk_index, level, importance,
                     access_count, last_access, created_at, source_ids)
                VALUES (?, ?, ?, 0.5, 0, ?, ?, '[]')
                """,
                (document_id, chunk_index, int(MemoryLevel.SENSORY), now, now),
            )
