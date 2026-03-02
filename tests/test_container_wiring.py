from cerebro_python.bootstrap.container import Container


def test_container_uses_memory_repository_when_configured(monkeypatch):
    monkeypatch.setenv("RAG_REPOSITORY_ADAPTER", "memory")
    monkeypatch.setenv("RAG_EMBEDDING_ADAPTER", "hash")
    monkeypatch.setenv("RAG_RANKER_ADAPTER", "hybrid")
    monkeypatch.setenv("RAG_MEMORY_POLICY_ADAPTER", "smart")
    monkeypatch.setenv("RAG_RERANKER_ADAPTER", "heuristic")
    monkeypatch.setenv("RAG_QUERY_REWRITER_ADAPTER", "rules")
    monkeypatch.setenv("RAG_SCOPE_STRATEGY_ADAPTER", "auto")

    container = Container()
    service = container.build_service()

    out = service.ingest(document_id="c1", text="test content for robust memory policy")
    assert out["status"] == "success"

    stats = service.stats()
    assert stats["storage"] == "memory"
    assert stats["documents"] == 1

    info = {
        "selected": container.selected_adapters(),
        "available": container.available_adapters(),
    }
    assert info["selected"]["ranker"] == "hybrid"
    assert info["selected"]["policy"] == "smart"
    assert info["selected"]["reranker"] == "heuristic"
    assert info["selected"]["query_rewriter"] == "rules"
    assert info["selected"]["scope_strategy"] == "auto"
    assert "hybrid" in info["available"]["ranker"]
    assert "smart" in info["available"]["policy"]
    assert "heuristic" in info["available"]["reranker"]
    assert "rules" in info["available"]["query_rewriter"]
    assert "auto" in info["available"]["scope_strategy"]
