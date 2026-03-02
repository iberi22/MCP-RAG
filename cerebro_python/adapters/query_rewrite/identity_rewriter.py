"""No-op query rewriter."""

from __future__ import annotations


class IdentityQueryRewriter:
    def rewrite(self, query: str) -> str:
        return query

