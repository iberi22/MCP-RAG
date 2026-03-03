"""OpenRouter LLM provider — calls OpenRouter API directly using urllib."""

from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
import re
from cerebro_python.domain.llm_provider import LLMProvider

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterLLMClient(LLMProvider):
    """Direct HTTP client for OpenRouter API."""

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENROUTER_API_KEY", "")
        self._model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def _chat(self, system: str, user: str, max_tokens: int = 256) -> str:
        if not self.is_available:
            return ""

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": max_tokens
        }).encode("utf-8")

        req = urllib.request.Request(
            _OPENROUTER_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "https://github.com/iberi22/MCP-RAG",
                "X-Title": "MCP-RAG"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return ""

    def score_importance(self, text: str, context: str) -> float:
        reply = self._chat(
            system="You are a memory importance evaluator. Reply with only a single integer 0–10.",
            user=f"Context: '{context}'\nRate the importance (0–10): '{text}'"
        )
        try:
            raw = "".join(ch for ch in reply if ch.isdigit() or ch == ".")
            return min(1.0, max(0.0, float(raw) / 10.0))
        except (ValueError, TypeError):
            return 0.5

    def consolidate(self, texts: list[str]) -> str:
        if not texts:
            return ""
        combined = "\n".join(f"- {t}" for t in texts)
        return self._chat(
            system="Given memory episodes, synthesize them into one concise semantic fact.",
            user=f"Episodes:\n{combined}"
        ) or " | ".join(texts[:3])

    def rewrite_query(self, query: str) -> str:
        if not query.strip():
            return query
        reply = self._chat(
            system='Expand technical search queries for RAG. Return only JSON: {"expanded_query":"...", "keywords":["..."]}',
            user=f"Original query: {query}"
        )
        if not reply:
            return query
        # Minimal JSON extraction
        try:
            match = re.search(r"\{.*\}", reply, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data.get("expanded_query", query)
        except Exception:
            pass
        return query

    def score_relevance(self, query: str, candidate_text: str) -> float:
        reply = self._chat(
            system="Strict reranker. Reply with only a number from 0 to 1.",
            user=f"Query: {query}\nCandidate: {candidate_text[:1000]}"
        )
        try:
            match = re.search(r"-?\d+(?:\.\d+)?", reply)
            return min(1.0, max(0.0, float(match.group(0)))) if match else 0.0
        except Exception:
            return 0.0
