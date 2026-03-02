"""In-memory repository adapter for tests and ephemeral sessions."""

from __future__ import annotations

from cerebro_python.domain.models import ChunkRecord, StorageStats


class InMemoryRepository:
    def __init__(self):
        self._rows: list[ChunkRecord] = []

    def replace_document(self, document_id: str, records: list[ChunkRecord]) -> int:
        self._rows = [row for row in self._rows if row.document_id != document_id]
        self._rows.extend(records)
        return len(records)

    def fetch_all_chunks(self) -> list[ChunkRecord]:
        return list(self._rows)

    def delete_document(self, document_id: str) -> int:
        before = len(self._rows)
        self._rows = [row for row in self._rows if row.document_id != document_id]
        return before - len(self._rows)

    def stats(self) -> StorageStats:
        documents = len({row.document_id for row in self._rows})
        chunks = len(self._rows)
        return StorageStats(
            storage="memory",
            documents=documents,
            chunks=chunks,
            details={"ephemeral": True},
        )
