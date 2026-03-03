"""MiniMax-powered query rewriter with deterministic fallback."""

from __future__ import annotations

import os

from cerebro_python.adapters.llm.minimax_client import MinimaxLLMClient
from cerebro_python.adapters.query_rewrite.rules_rewriter import RulesQueryRewriter


class MinimaxQueryRewriter:
    """Rewrite search queries using MiniMax and fall back to rules."""

    def __init__(
        self,
        llm_client: MinimaxLLMClient | None = None,
        fallback: RulesQueryRewriter | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._llm = llm_client or MinimaxLLMClient()
        self._fallback = fallback or RulesQueryRewriter()
        self._max_tokens = max_tokens or int(os.getenv("RAG_LLM_REWRITE_MAX_TOKENS", "96"))

    def rewrite(self, query: str) -> str:
        if not query.strip():
            return query
        if not self._llm.is_available:
            return self._fallback.rewrite(query)
        rewritten = self._llm.rewrite_query(query=query, max_tokens=self._max_tokens).strip()
        if not rewritten:
            return self._fallback.rewrite(query)
        return rewritten
