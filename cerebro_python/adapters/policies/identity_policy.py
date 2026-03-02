"""No-op memory policy adapter."""

from __future__ import annotations

from cerebro_python.domain.models import ChunkRecord


class IdentityMemoryPolicy:
    def sanitize_records(self, records: list[ChunkRecord]) -> list[ChunkRecord]:
        return list(records)

