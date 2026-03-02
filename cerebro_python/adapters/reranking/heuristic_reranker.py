"""Heuristic reranker: phrase + token coverage over base score."""

from __future__ import annotations

import re

from cerebro_python.domain.models import SearchHit

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class HeuristicRerankerAdapter:
    def __init__(self, base_weight: float = 0.7, lexical_weight: float = 0.3, phrase_boost: float = 0.1):
        self._base_weight = max(0.0, min(1.0, base_weight))
        self._lexical_weight = max(0.0, min(1.0, lexical_weight))
        self._phrase_boost = max(0.0, phrase_boost)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(_TOKEN_RE.findall(text.lower()))

    def rerank(self, query: str, hits: list[SearchHit], top_k: int) -> list[SearchHit]:
        qtokens = self._tokens(query)
        qnorm = " ".join(_TOKEN_RE.findall(query.lower()))
        rescored: list[SearchHit] = []
        for hit in hits:
            htoks = self._tokens(hit.chunk_text)
            lexical = (len(qtokens & htoks) / len(qtokens)) if qtokens else 0.0
            phrase = self._phrase_boost if (qnorm and qnorm in hit.chunk_text.lower()) else 0.0
            score = (hit.score * self._base_weight) + (lexical * self._lexical_weight) + phrase
            rescored.append(
                SearchHit(
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    chunk_text=hit.chunk_text,
                    score=score,
                    metadata=hit.metadata,
                )
            )
        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[: max(1, top_k)]

