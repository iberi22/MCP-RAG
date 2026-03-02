"""Rule-based query rewriter for compact recall gains."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class RulesQueryRewriter:
    def __init__(self, synonyms: dict[str, list[str]] | None = None):
        self._synonyms = synonyms or {
            "agent": ["agents", "assistant"],
            "agents": ["agent", "assistant"],
            "memory": ["context", "knowledge"],
            "rag": ["retrieval", "retrieval_augmented_generation"],
            "code": ["coding", "development"],
            "bug": ["issue", "error"],
        }

    def rewrite(self, query: str) -> str:
        tokens = _TOKEN_RE.findall(query.lower())
        if not tokens:
            return query
        out: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token not in seen:
                out.append(token)
                seen.add(token)
            for alt in self._synonyms.get(token, []):
                if alt not in seen:
                    out.append(alt)
                    seen.add(alt)
        return " ".join(out)

