"""MiniMax LLM client — calls the Anthropic-compatible Messages API directly.

Endpoint : https://api.minimax.io/anthropic/v1/messages
Auth     : x-api-key header  (same key from platform.minimax.io)
Format   : standard Anthropic Messages API (role/content blocks)
Models   : MiniMax-M2.5, MiniMax-M2.5-highspeed, MiniMax-M2.1, MiniMax-M2.1-highspeed

Uses only Python stdlib (json + urllib.request) — no extra pip deps needed.
Falls back gracefully when MINIMAX_API_KEY is not set.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import re
from cerebro_python.domain.llm_provider import LLMProvider

_MESSAGES_URL = "https://api.minimax.io/anthropic/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class MinimaxLLMClient(LLMProvider):
    """Direct HTTP client for the MiniMax Anthropic-compatible Messages API."""

    def __init__(self) -> None:
        self._api_key = os.getenv("MINIMAX_API_KEY", "")
        self._model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def _chat(self, system: str, user: str, max_tokens: int = 256) -> str:
        if not self.is_available:
            return ""

        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": user}],
                    }
                ],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            _MESSAGES_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block["text"].strip()
                return ""
        except Exception:
            return ""

    def score_importance(self, text: str, context: str) -> float:
        reply = self._chat(
            system="You are a memory importance evaluator. Reply with only a single integer 0–10.",
            user=f"Context: '{context}'\nRate the importance of this memory (0–10): '{text}'",
            max_tokens=8,
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
        reply = self._chat(
            system="Synthesise related memory episodes into one concise semantic fact.",
            user=f"Episodes:\n{combined}",
            max_tokens=200,
        )
        return reply or " | ".join(t[:120] for t in texts[:3])

    def rewrite_query(self, query: str, max_tokens: int = 96) -> str:
        if not query.strip():
            return query
        reply = self._chat(
            system='Expand technical search queries for RAG. Return JSON: {"expanded_query":"...", "keywords":["..."]}',
            user=f"Original query: {query}",
            max_tokens=max_tokens,
        )
        if not reply:
            return query
        try:
            payload = self._extract_json(reply)
            return str(payload.get("expanded_query", query)).strip()
        except Exception:
            return query

    def score_relevance(self, query: str, candidate_text: str, max_tokens: int = 12) -> float:
        if not query.strip() or not candidate_text.strip():
            return 0.0
        reply = self._chat(
            system="Strict reranker. Reply with only a number from 0 to 1.",
            user=f"Query: {query}\nCandidate: {candidate_text[:1500]}",
            max_tokens=max_tokens,
        )
        try:
            match = re.search(r"-?\d+(?:\.\d+)?", reply)
            return min(1.0, max(0.0, float(match.group(0)))) if match else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("No JSON object found")
