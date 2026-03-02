from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter
from cerebro_python.adapters.policies.smart_memory_policy import SmartMemoryPolicy
from cerebro_python.domain.models import ChunkRecord


def test_smart_policy_filters_short_and_duplicates_and_reindexes():
    embedder = HashEmbeddingAdapter(dims=128)
    policy = SmartMemoryPolicy(min_chunk_chars=10, max_chunks_per_document=4)
    records = [
        ChunkRecord("d1", 0, "short", embedder.embed("short"), {}),
        ChunkRecord("d1", 1, "memoria robusta para agentes", embedder.embed("memoria robusta para agentes"), {}),
        ChunkRecord("d1", 2, "memoria robusta para agentes", embedder.embed("memoria robusta para agentes"), {}),
        ChunkRecord("d1", 3, "arquitectura hexagonal desacoplada", embedder.embed("arquitectura hexagonal desacoplada"), {}),
    ]

    out = policy.sanitize_records(records)
    assert len(out) == 2
    assert out[0].chunk_index == 0
    assert out[1].chunk_index == 1

