"""SQLite repository adapter."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from cerebro_python.domain.models import ChunkRecord, StorageStats


class SqliteMemoryRepository:
    def __init__(self, db_path: str = "cerebro_rag.db"):
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        Path(self._db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rag_chunks_document ON rag_chunks(document_id, chunk_index)"
            )

    def replace_document(self, document_id: str, records: list[ChunkRecord]) -> int:
        with self._connect() as conn:
            conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
            for record in records:
                conn.execute(
                    """
                    INSERT INTO rag_chunks(document_id, chunk_index, chunk_text, embedding, metadata)
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        record.document_id,
                        record.chunk_index,
                        record.chunk_text,
                        json.dumps(record.embedding),
                        json.dumps(record.metadata),
                    ),
                )
        return len(records)

    def fetch_all_chunks(self) -> list[ChunkRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT document_id, chunk_index, chunk_text, embedding, metadata FROM rag_chunks"
            ).fetchall()
        return [
            ChunkRecord(
                document_id=row["document_id"],
                chunk_index=int(row["chunk_index"]),
                chunk_text=row["chunk_text"],
                embedding=[float(x) for x in json.loads(row["embedding"])],
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    def delete_document(self, document_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
        return int(cursor.rowcount)

    def stats(self) -> StorageStats:
        with self._connect() as conn:
            chunk_count = conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()[0]
            doc_count = conn.execute("SELECT COUNT(DISTINCT document_id) FROM rag_chunks").fetchone()[0]
        return StorageStats(
            storage="sqlite",
            documents=int(doc_count),
            chunks=int(chunk_count),
            details={"db_path": str(Path(self._db_path).resolve())},
        )
