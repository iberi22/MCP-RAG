"""Hybrid ranker adapter: semantic + lexical + MMR + dedupe."""

from __future__ import annotations

import re

from cerebro_python.domain.models import ChunkRecord, SearchHit

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class HybridRankerAdapter:
    def __init__(self, semantic_weight: float = 0.75, lexical_weight: float = 0.25, rrf_k: int = 50, mmr_lambda: float = 0.75):
        self._semantic_weight = max(0.0, min(1.0, semantic_weight))
        self._lexical_weight = max(0.0, min(1.0, lexical_weight))
        self._rrf_k = max(10, rrf_k)
        self._mmr_lambda = max(0.1, min(0.95, mmr_lambda))

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=False))

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(_TOKEN_RE.findall(text.lower()))

    def rank(self, query: str, query_vector: list[float], chunks: list[ChunkRecord], top_k: int) -> list[SearchHit]:
        if not chunks:
            return []

        qtokens = self._tokens(query)
        scored: list[tuple[int, float, float]] = []
        for idx, chunk in enumerate(chunks):
            sem = self._cosine(query_vector, chunk.embedding)
            ctokens = self._tokens(chunk.chunk_text)
            lex = (len(qtokens & ctokens) / len(qtokens)) if qtokens else 0.0
            scored.append((idx, sem, lex))

        sem_rank = {idx: pos for pos, (idx, _, _) in enumerate(sorted(scored, key=lambda s: s[1], reverse=True), start=1)}
        lex_rank = {idx: pos for pos, (idx, _, _) in enumerate(sorted(scored, key=lambda s: s[2], reverse=True), start=1)}

        candidates: list[tuple[int, float]] = []
        for idx, sem, lex in scored:
            rrf = (1.0 / (self._rrf_k + sem_rank[idx])) + (1.0 / (self._rrf_k + lex_rank[idx]))
            blended = (sem * self._semantic_weight) + (lex * self._lexical_weight)
            candidates.append((idx, blended + rrf))
        candidates.sort(key=lambda it: it[1], reverse=True)
        candidate_scores = {idx: score for idx, score in candidates}

        selected: list[int] = []
        seen_text: set[str] = set()
        max_candidates = max(top_k * 4, top_k)
        for idx, _ in candidates[:max_candidates]:
            signature = " ".join(_TOKEN_RE.findall(chunks[idx].chunk_text.lower())[:32])
            if signature in seen_text:
                continue
            seen_text.add(signature)
            if not selected:
                selected.append(idx)
            else:
                relevance = candidate_scores[idx]
                max_sim = max(self._cosine(chunks[idx].embedding, chunks[s].embedding) for s in selected)
                mmr = (self._mmr_lambda * relevance) - ((1.0 - self._mmr_lambda) * max_sim)
                if mmr > -0.1:
                    selected.append(idx)
            if len(selected) >= top_k:
                break

        if len(selected) < top_k:
            for idx, _ in candidates:
                if idx not in selected:
                    selected.append(idx)
                if len(selected) >= top_k:
                    break

        return [
            SearchHit(
                document_id=chunks[idx].document_id,
                chunk_index=chunks[idx].chunk_index,
                chunk_text=chunks[idx].chunk_text,
                score=candidate_scores[idx],
                metadata=chunks[idx].metadata,
            )
            for idx in selected[:top_k]
        ]
