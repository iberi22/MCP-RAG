from cerebro_python.adapters.query_rewrite.rules_rewriter import RulesQueryRewriter


def test_rules_query_rewriter_expands_synonyms():
    rewriter = RulesQueryRewriter()
    out = rewriter.rewrite("agent memory")
    assert "agent" in out
    assert "agents" in out
    assert "assistant" in out
    assert "memory" in out
    assert "context" in out

