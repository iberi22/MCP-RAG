from cerebro_python.adapters.chunking.simple_chunker import SimpleChunker
from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter
from cerebro_python.adapters.query_rewrite.rules_rewriter import RulesQueryRewriter
from cerebro_python.adapters.storage.inmemory_repository import InMemoryRepository
from cerebro_python.application.use_cases import RagService


def build_service() -> RagService:
    return RagService(
        repository=InMemoryRepository(),
        chunker=SimpleChunker(chunk_size=200, chunk_overlap=20),
        embedder=HashEmbeddingAdapter(dims=128),
    )


def test_rag_service_ingest_search_delete_stats():
    service = build_service()

    ingest = service.ingest(
        document_id="doc-1",
        text="Arquitectura hexagonal para memoria robusta de agentes.",
        metadata={"source": "test"},
    )
    assert ingest["status"] == "success"
    assert ingest["chunks"] >= 1

    hits = service.search(query="memoria agentes", top_k=3)
    assert len(hits) >= 1
    assert hits[0].document_id == "doc-1"

    stats = service.stats()
    assert stats["status"] == "success"
    assert stats["documents"] == 1

    deleted = service.delete("doc-1")
    assert deleted["deleted_chunks"] >= 1

    stats_after = service.stats()
    assert stats_after["documents"] == 0


def test_rag_service_search_min_score_filters_results():
    service = build_service()
    service.ingest(document_id="doc-relevant", text="agent memory architecture")
    service.ingest(document_id="doc-other", text="cooking recipes and ingredients")

    hits = service.search(query="agent memory", top_k=5, min_score=0.6)
    assert len(hits) >= 1
    assert all(hit.score >= 0.6 for hit in hits)


def test_query_rewriter_improves_recall_for_synonyms():
    repo = InMemoryRepository()
    chunker = SimpleChunker(chunk_size=200, chunk_overlap=20)
    embedder = HashEmbeddingAdapter(dims=128)
    service_plain = RagService(repository=repo, chunker=chunker, embedder=embedder)
    service_rewrite = RagService(repository=repo, chunker=chunker, embedder=embedder, query_rewriter=RulesQueryRewriter())

    service_plain.ingest(document_id="doc-ctx", text="context knowledge for coding assistant memory")
    no_rewrite_hits = service_plain.search(query="memoryy", top_k=5, min_score=0.1)
    rewrite_hits = service_rewrite.search(query="agent", top_k=5, min_score=0.1)

    assert len(no_rewrite_hits) == 0
    assert len(rewrite_hits) >= 1
