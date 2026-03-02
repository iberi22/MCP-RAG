"""Deterministic hash embedding adapter (pure Python)."""

from __future__ import annotations

import math
import re
from hashlib import blake2b

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class HashEmbeddingAdapter:
    def __init__(self, dims: int = 256):
        self._dims = max(64, dims)

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dims
        for token in _TOKEN_RE.findall(text.lower()):
            token_hash = int.from_bytes(blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
            vector[token_hash % self._dims] += 1.0

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]
