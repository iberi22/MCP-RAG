from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter
from cerebro_python.adapters.ranking.hybrid_ranker import HybridRankerAdapter
from cerebro_python.domain.models import ChunkRecord


def test_hybrid_ranker_prioritizes_relevant_text():
    embedder = HashEmbeddingAdapter(dims=128)
    ranker = HybridRankerAdapter()
    chunks = [
        ChunkRecord("doc-a", 0, "memoria de agentes con arquitectura hexagonal", embedder.embed("memoria de agentes con arquitectura hexagonal"), {}),
        ChunkRecord("doc-b", 0, "recetas de cocina italiana", embedder.embed("recetas de cocina italiana"), {}),
    ]

    hits = ranker.rank(
        query="memoria agentes",
        query_vector=embedder.embed("memoria agentes"),
        chunks=chunks,
        top_k=1,
    )
    assert len(hits) == 1
    assert hits[0].document_id == "doc-a"


def test_hybrid_ranker_deduplicates_same_content():
    embedder = HashEmbeddingAdapter(dims=128)
    ranker = HybridRankerAdapter()
    shared = "memoria semantica para agentes de codigo"
    chunks = [
        ChunkRecord("doc-a", 0, shared, embedder.embed(shared), {}),
        ChunkRecord("doc-b", 0, shared, embedder.embed(shared), {}),
        ChunkRecord("doc-c", 0, "sistema de embeddings local", embedder.embed("sistema de embeddings local"), {}),
    ]

    hits = ranker.rank(
        query="memoria semantica",
        query_vector=embedder.embed("memoria semantica"),
        chunks=chunks,
        top_k=2,
    )
    assert len(hits) == 2
    assert len({h.chunk_text for h in hits}) == 2

