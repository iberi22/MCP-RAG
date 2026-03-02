from cerebro_python.adapters.reranking.heuristic_reranker import HeuristicRerankerAdapter
from cerebro_python.domain.models import SearchHit


def test_heuristic_reranker_boosts_phrase_match():
    reranker = HeuristicRerankerAdapter(base_weight=0.7, lexical_weight=0.2, phrase_boost=0.4)
    hits = [
        SearchHit("a", 0, "coding memory patterns for agents", 0.8, {}),
        SearchHit("b", 0, "this chunk includes exact phrase coding agents memory", 0.75, {}),
    ]
    out = reranker.rerank(query="coding agents memory", hits=hits, top_k=2)
    assert len(out) == 2
    assert out[0].document_id == "b"
