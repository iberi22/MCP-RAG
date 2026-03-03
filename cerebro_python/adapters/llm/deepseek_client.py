"""DeepSeek LLM provider — calls DeepSeek API directly using urllib."""

from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
import re
from cerebro_python.domain.llm_provider import LLMProvider

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

class DeepSeekLLMClient(LLMProvider):
    """Direct HTTP client for DeepSeek API."""

    def __init__(self) -> None:
        self._api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self._model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

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
            "max_tokens": max_tokens,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            _DEEPSEEK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}"
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
            system="Memory importance evaluator (0-10).",
            user=f"Context: {context}\nMemory: {text}"
        )
        try:
            match = re.search(r"\d+", reply)
            return min(1.0, max(0.0, float(match.group(0)) / 10.0)) if match else 0.5
        except:
            return 0.5

    def consolidate(self, texts: list[str]) -> str:
        if not texts: return ""
        return self._chat(
            system="Synthesize memory episodes into one fact.",
            user="\n".join(texts)
        ) or " | ".join(texts[:3])

    def rewrite_query(self, query: str) -> str:
        if not query.strip(): return query
        reply = self._chat(
            system="Expand search query. Return only expanded text.",
            user=query
        )
        return reply or query

    def score_relevance(self, query: str, candidate_text: str) -> float:
        reply = self._chat(
            system="Reranker (0 to 1).",
            user=f"Q: {query}\nC: {candidate_text[:1000]}"
        )
        try:
            match = re.search(r"-?\d+(?:\.\d+)?", reply)
            return min(1.0, max(0.0, float(match.group(0)))) if match else 0.0
        except:
            return 0.0
