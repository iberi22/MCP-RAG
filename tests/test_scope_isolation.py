from cerebro_python.adapters.chunking.simple_chunker import SimpleChunker
from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter
from cerebro_python.adapters.query_rewrite.identity_rewriter import IdentityQueryRewriter
from cerebro_python.adapters.scope.auto_scope_strategy import AutoScopeStrategy
from cerebro_python.adapters.storage.inmemory_repository import InMemoryRepository
from cerebro_python.application.use_cases import RagService


def _service() -> RagService:
    return RagService(
        repository=InMemoryRepository(),
        chunker=SimpleChunker(chunk_size=300, chunk_overlap=20),
        embedder=HashEmbeddingAdapter(dims=128),
        query_rewriter=IdentityQueryRewriter(),
        scope_strategy=AutoScopeStrategy(),
    )


def test_search_scoped_isolates_project_and_environment():
    service = _service()
    service.ingest(
        document_id="alpha-dev-1",
        text="alpha project coding standards and internal architecture",
        metadata={"project_id": "alpha", "environment_id": "dev"},
    )
    service.ingest(
        document_id="beta-dev-1",
        text="beta project coding standards and internal architecture",
        metadata={"project_id": "beta", "environment_id": "dev"},
    )
    service.ingest(
        document_id="alpha-prod-1",
        text="alpha production deployment runbook and release gates",
        metadata={"project_id": "alpha", "environment_id": "prod"},
    )

    hits = service.search_scoped(
        query="coding standards architecture",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
    )
    assert len(hits) >= 1
    assert all(h.metadata.get("project_id") == "alpha" for h in hits)
    assert all(h.metadata.get("environment_id") == "dev" for h in hits)


def test_search_scoped_can_include_additional_environment():
    service = _service()
    service.ingest(
        document_id="alpha-dev",
        text="alpha development checklist",
        metadata={"project_id": "alpha", "environment_id": "dev"},
    )
    service.ingest(
        document_id="alpha-prod",
        text="alpha production rollback checklist",
        metadata={"project_id": "alpha", "environment_id": "prod"},
    )

    strict_hits = service.search_scoped(
        query="rollback checklist",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
    )
    expanded_hits = service.search_scoped(
        query="rollback checklist",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        include_environment_ids=["prod"],
        scope_mode="custom",
    )

    assert all(h.metadata.get("environment_id") == "dev" for h in strict_hits)
    assert any(h.metadata.get("environment_id") == "prod" for h in expanded_hits)


def test_search_scoped_auto_mode_can_expand_environment():
    service = _service()
    service.ingest(
        document_id="alpha-dev",
        text="alpha development checklist",
        metadata={"project_id": "alpha", "environment_id": "dev"},
    )
    service.ingest(
        document_id="alpha-prod",
        text="alpha production rollback checklist",
        metadata={"project_id": "alpha", "environment_id": "prod"},
    )

    strict_hits = service.search_scoped(
        query="rollback release process",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        scope_mode="strict",
    )
    auto_hits = service.search_scoped(
        query="rollback release process",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        scope_mode="auto",
    )

    assert all(h.metadata.get("environment_id") == "dev" for h in strict_hits)
    assert any(h.metadata.get("environment_id") == "prod" for h in auto_hits)


def test_search_scoped_prefers_latest_fact_key():
    service = _service()
    service.ingest(
        document_id="alpha-rule-v1",
        text="alpha deployment rule old",
        metadata={
            "project_id": "alpha",
            "environment_id": "dev",
            "fact_key": "deploy_rule",
            "event_time": "2025-01-01T00:00:00+00:00",
        },
    )
    service.ingest(
        document_id="alpha-rule-v2",
        text="alpha deployment rule new",
        metadata={
            "project_id": "alpha",
            "environment_id": "dev",
            "fact_key": "deploy_rule",
            "event_time": "2026-01-01T00:00:00+00:00",
        },
    )

    hits = service.search_scoped(
        query="deployment rule",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
    )
    docs = {h.document_id for h in hits}
    assert "alpha-rule-v2" in docs
    assert "alpha-rule-v1" not in docs


def test_search_scoped_event_time_cutoff_filters_future_events():
    service = _service()
    service.ingest(
        document_id="alpha-now",
        text="alpha current architecture",
        metadata={"project_id": "alpha", "environment_id": "dev", "event_time": "2025-01-01T00:00:00+00:00"},
    )
    service.ingest(
        document_id="alpha-future",
        text="alpha future architecture plan",
        metadata={"project_id": "alpha", "environment_id": "dev", "event_time": "2027-01-01T00:00:00+00:00"},
    )

    hits = service.search_scoped(
        query="architecture",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        event_time_at="2025-12-31T23:59:59+00:00",
    )
    docs = {h.document_id for h in hits}
    assert "alpha-now" in docs
    assert "alpha-future" not in docs
