"""Smart memory policy: normalize, filter, dedupe and cap per document."""

from __future__ import annotations

import re

from cerebro_python.domain.models import ChunkRecord

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class SmartMemoryPolicy:
    def __init__(self, min_chunk_chars: int = 24, max_chunks_per_document: int = 128):
        self._min_chunk_chars = max(1, min_chunk_chars)
        self._max_chunks_per_document = max(1, max_chunks_per_document)

    @staticmethod
    def _normalize(text: str) -> str:
        return _WS_RE.sub(" ", text).strip()

    @staticmethod
    def _signature(text: str) -> str:
        return " ".join(_TOKEN_RE.findall(text.lower())[:48])

    def sanitize_records(self, records: list[ChunkRecord]) -> list[ChunkRecord]:
        out: list[ChunkRecord] = []
        seen: set[str] = set()
        for record in records:
            normalized = self._normalize(record.chunk_text)
            if len(normalized) < self._min_chunk_chars:
                continue
            sig = self._signature(normalized)
            if not sig or sig in seen:
                continue
            seen.add(sig)
            out.append(
                ChunkRecord(
                    document_id=record.document_id,
                    chunk_index=len(out),
                    chunk_text=normalized,
                    embedding=record.embedding,
                    metadata=record.metadata,
                )
            )
            if len(out) >= self._max_chunks_per_document:
                break
        return out

