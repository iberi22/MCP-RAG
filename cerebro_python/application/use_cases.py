"""Application use cases."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from cerebro_python.domain.models import ChunkRecord, SearchHit
from cerebro_python.domain.ports import (
    ChunkingPort,
    EmbeddingPort,
    MemoryPolicyPort,
    MemoryRepositoryPort,
    QueryRewritePort,
    RankerPort,
    RerankerPort,
    ScopeStrategyPort,
)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class RagService:
    def __init__(
        self,
        repository: MemoryRepositoryPort,
        chunker: ChunkingPort,
        embedder: EmbeddingPort,
        ranker: RankerPort | None = None,
        memory_policy: MemoryPolicyPort | None = None,
        reranker: RerankerPort | None = None,
        query_rewriter: QueryRewritePort | None = None,
        scope_strategy: ScopeStrategyPort | None = None,
        retrieval_multiplier: int = 4,
        min_score: float = -1.0,
    ):
        self._repository = repository
        self._chunker = chunker
        self._embedder = embedder
        self._ranker = ranker
        self._memory_policy = memory_policy
        self._reranker = reranker
        self._query_rewriter = query_rewriter
        self._scope_strategy = scope_strategy
        self._retrieval_multiplier = max(1, retrieval_multiplier)
        self._min_score = min_score

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=False))

    def ingest(self, document_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        chunks = self._chunker.split(text)
        if not chunks:
            return {"status": "error", "error": "empty_text", "document_id": document_id}

        base_meta = metadata or {}
        if "ingested_at" not in base_meta:
            base_meta["ingested_at"] = datetime.now(timezone.utc).isoformat()
        records: list[ChunkRecord] = []
        for index, chunk in enumerate(chunks):
            records.append(
                ChunkRecord(
                    document_id=document_id,
                    chunk_index=index,
                    chunk_text=chunk,
                    embedding=self._embedder.embed(chunk),
                    metadata=dict(base_meta),
                )
            )

        if self._memory_policy is not None:
            records = self._memory_policy.sanitize_records(records)
        if not records:
            return {"status": "error", "error": "all_chunks_filtered", "document_id": document_id}

        stored = self._repository.replace_document(document_id=document_id, records=records)
        return {"status": "success", "document_id": document_id, "chunks": stored}

    def search(self, query: str, top_k: int = 5, min_score: float | None = None) -> list[SearchHit]:
        return self.search_scoped(query=query, top_k=top_k, min_score=min_score)

    def search_scoped(
        self,
        query: str,
        top_k: int = 5,
        min_score: float | None = None,
        project_id: str | None = None,
        environment_id: str | None = None,
        include_environment_ids: list[str] | None = None,
        scope_mode: str = "strict",
        event_time_at: str | None = None,
        ingested_before: str | None = None,
        include_inactive: bool = False,
        prefer_latest_facts: bool = True,
    ) -> list[SearchHit]:
        top_k = max(1, top_k)
        candidate_k = max(top_k, top_k * self._retrieval_multiplier)
        effective_min_score = self._min_score if min_score is None else min_score
        effective_query = self._query_rewriter.rewrite(query) if self._query_rewriter is not None else query
        additional_envs = self._resolve_additional_envs(
            query=effective_query,
            environment_id=environment_id,
            include_environment_ids=include_environment_ids,
            scope_mode=scope_mode,
        )
        qvec = self._embedder.embed(effective_query)
        chunks = self._filter_chunks_by_scope(
            self._repository.fetch_all_chunks(),
            project_id=project_id,
            environment_id=environment_id,
            include_environment_ids=additional_envs,
            event_time_at=event_time_at,
            ingested_before=ingested_before,
            include_inactive=include_inactive,
        )
        if self._ranker is not None:
            hits = self._ranker.rank(query=effective_query, query_vector=qvec, chunks=chunks, top_k=candidate_k)
            if self._reranker is not None:
                hits = self._reranker.rerank(query=effective_query, hits=hits, top_k=candidate_k)
            if prefer_latest_facts:
                hits = self._prefer_latest_fact_hits(hits)
            return [h for h in hits if h.score >= effective_min_score][:top_k]

        # Fallback minimal ranker: cosine + lexical overlap.
        qtokens = set(_TOKEN_RE.findall(effective_query.lower()))
        hits: list[SearchHit] = []
        for chunk in chunks:
            ctokens = set(_TOKEN_RE.findall(chunk.chunk_text.lower()))
            lexical = (len(qtokens & ctokens) / len(qtokens)) if qtokens else 0.0
            hits.append(
                SearchHit(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    score=(self._cosine(qvec, chunk.embedding) * 0.8) + (lexical * 0.2),
                    metadata=chunk.metadata,
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        if prefer_latest_facts:
            hits = self._prefer_latest_fact_hits(hits)
        return [h for h in hits if h.score >= effective_min_score][:top_k]

    def _resolve_additional_envs(
        self,
        query: str,
        environment_id: str | None,
        include_environment_ids: list[str] | None,
        scope_mode: str,
    ) -> list[str]:
        if self._scope_strategy is None:
            if scope_mode == "strict":
                return []
            requested = [env for env in (include_environment_ids or []) if env and env != environment_id]
            return sorted(set(requested))
        return self._scope_strategy.select_additional_environments(
            query=query,
            environment_id=environment_id,
            requested_environment_ids=include_environment_ids,
            scope_mode=scope_mode,
        )

    @staticmethod
    def _filter_chunks_by_scope(
        chunks: list[ChunkRecord],
        project_id: str | None,
        environment_id: str | None,
        include_environment_ids: list[str] | None,
        event_time_at: str | None,
        ingested_before: str | None,
        include_inactive: bool,
    ) -> list[ChunkRecord]:
        event_cutoff = RagService._parse_dt(event_time_at)
        ingest_cutoff = RagService._parse_dt(ingested_before)
        allowed_envs: set[str] = set(include_environment_ids or [])
        if environment_id:
            allowed_envs.add(environment_id)
        filter_by_env = bool(allowed_envs)

        out: list[ChunkRecord] = []
        for chunk in chunks:
            meta = chunk.metadata or {}
            if project_id and str(meta.get("project_id", "")) != project_id:
                continue
            if filter_by_env and str(meta.get("environment_id", "")) not in allowed_envs:
                continue
            if not include_inactive and meta.get("active") is False:
                continue
            if event_cutoff is not None:
                event_dt = RagService._parse_dt(str(meta.get("event_time", "")))
                if event_dt is not None and event_dt > event_cutoff:
                    continue
            if ingest_cutoff is not None:
                ingest_dt = RagService._parse_dt(str(meta.get("ingested_at", "")))
                if ingest_dt is not None and ingest_dt > ingest_cutoff:
                    continue
            out.append(chunk)
        return out

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _prefer_latest_fact_hits(hits: list[SearchHit]) -> list[SearchHit]:
        grouped: dict[str, SearchHit] = {}
        passthrough: list[SearchHit] = []
        for hit in hits:
            fact_key = str(hit.metadata.get("fact_key", "")).strip()
            if not fact_key:
                passthrough.append(hit)
                continue
            current = grouped.get(fact_key)
            if current is None:
                grouped[fact_key] = hit
                continue
            if RagService._is_newer_fact(hit, current):
                grouped[fact_key] = hit
        merged = passthrough + list(grouped.values())
        merged.sort(key=lambda item: item.score, reverse=True)
        return merged

    @staticmethod
    def _is_newer_fact(candidate: SearchHit, existing: SearchHit) -> bool:
        c_event = RagService._parse_dt(str(candidate.metadata.get("event_time", "")))
        e_event = RagService._parse_dt(str(existing.metadata.get("event_time", "")))
        if c_event and e_event and c_event != e_event:
            return c_event > e_event
        c_ing = RagService._parse_dt(str(candidate.metadata.get("ingested_at", "")))
        e_ing = RagService._parse_dt(str(existing.metadata.get("ingested_at", "")))
        if c_ing and e_ing and c_ing != e_ing:
            return c_ing > e_ing
        return candidate.score > existing.score

    def delete(self, document_id: str) -> dict[str, Any]:
        deleted = self._repository.delete_document(document_id)
        return {"status": "success", "document_id": document_id, "deleted_chunks": deleted}

    def stats(self) -> dict[str, Any]:
        st = self._repository.stats()
        return {
            "status": "success",
            "storage": st.storage,
            "documents": st.documents,
            "chunks": st.chunks,
            **st.details,
        }

# Backward compatibility alias
RagUseCases = RagService
