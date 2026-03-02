"""Backward-compatible facade over hexagonal RagService."""

from __future__ import annotations

from typing import Any

from cerebro_python.bootstrap.container import Container
from cerebro_python.domain.models import SearchHit


class RAGStore:
    def __init__(self):
        self._service = Container().build_service()

    def ingest(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._service.ingest(document_id=document_id, text=text, metadata=metadata)

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        return self._service.search(query=query, top_k=top_k)

    def delete(self, document_id: str) -> dict[str, Any]:
        return self._service.delete(document_id=document_id)

    def stats(self) -> dict[str, Any]:
        return self._service.stats()
