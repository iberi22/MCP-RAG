from cerebro_python.adapters.query_rewrite.minimax_rewriter import MinimaxQueryRewriter


class _LLMOk:
    is_available = True

    def rewrite_query(self, query: str, max_tokens: int = 96) -> str:
        return f"{query} oauth jwt session"


class _LLMFail:
    is_available = False

    def rewrite_query(self, query: str, max_tokens: int = 96) -> str:
        return query


def test_minimax_query_rewriter_uses_llm_expansion():
    rewriter = MinimaxQueryRewriter(llm_client=_LLMOk())
    out = rewriter.rewrite("auth")
    assert "auth" in out
    assert "oauth" in out
    assert "jwt" in out


def test_minimax_query_rewriter_falls_back_to_rules_when_unavailable():
    rewriter = MinimaxQueryRewriter(llm_client=_LLMFail())
    out = rewriter.rewrite("agent memory")
    assert "assistant" in out
    assert "context" in out
