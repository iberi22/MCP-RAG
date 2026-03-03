"""Domain models for symbol indexing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SymbolRecord:
    symbol_id: str
    file_path: str
    qualified_name: str
    kind: str
    language: str
    byte_start: int
    byte_end: int
    signature: str
