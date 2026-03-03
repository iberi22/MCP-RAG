from cerebro_python.adapters.reranking.minimax_reranker import MinimaxRerankerAdapter
from cerebro_python.domain.models import SearchHit


class _LLMScorer:
    is_available = True

    def score_relevance(self, query: str, candidate_text: str, max_tokens: int = 12) -> float:
        if "exact phrase" in candidate_text:
            return 1.0
        return 0.2


class _LLMUnavailable:
    is_available = False

    def score_relevance(self, query: str, candidate_text: str, max_tokens: int = 12) -> float:
        return 0.0


def test_minimax_reranker_reorders_by_llm_score():
    reranker = MinimaxRerankerAdapter(llm_client=_LLMScorer(), blend_weight=0.6, top_n=2)
    hits = [
        SearchHit("a", 0, "generic content", 0.9, {}),
        SearchHit("b", 0, "contains exact phrase for query", 0.6, {}),
    ]
    out = reranker.rerank(query="query", hits=hits, top_k=2)
    assert out[0].document_id == "b"


def test_minimax_reranker_fallbacks_to_heuristic_when_unavailable():
    reranker = MinimaxRerankerAdapter(llm_client=_LLMUnavailable(), top_n=2)
    hits = [
        SearchHit("a", 0, "coding memory patterns for agents", 0.8, {}),
        SearchHit("b", 0, "this chunk includes exact phrase coding agents memory", 0.75, {}),
    ]
    out = reranker.rerank(query="coding agents memory", hits=hits, top_k=2)
    assert out[0].document_id == "b"
