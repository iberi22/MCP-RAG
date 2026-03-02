"""MiniMax LLM client — calls the Anthropic-compatible Messages API directly.

Endpoint : https://api.minimax.io/anthropic/v1/messages
Auth     : x-api-key header  (same key from platform.minimax.io)
Format   : standard Anthropic Messages API (role/content blocks)
Models   : MiniMax-M2.5, MiniMax-M2.5-highspeed, MiniMax-M2.1, MiniMax-M2.1-highspeed

Uses only Python stdlib (json + urllib.request) — no extra pip deps needed.
Falls back gracefully when MINIMAX_API_KEY is not set:
  - score_importance returns 0.5 (neutral)
  - consolidate returns a simple text join
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


_MESSAGES_URL = "https://api.minimax.io/anthropic/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class MinimaxLLMClient:
    """Direct HTTP client for the MiniMax Anthropic-compatible Messages API."""

    def __init__(self) -> None:
        self._api_key = os.getenv("MINIMAX_API_KEY", "")
        self._model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    def _chat(self, system: str, user: str, max_tokens: int = 256) -> str:
        """POST to the Anthropic-compatible endpoint and return the text reply.

        Returns an empty string on any error so callers use their fallback.
        """
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
                # Anthropic response: data["content"] is a list of blocks
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block["text"].strip()
                return ""
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            # Don't crash — just return empty so fallback takes over
            _ = f"HTTPError {exc.code}: {body}"
            return ""
        except Exception:  # noqa: BLE001
            return ""

    # ------------------------------------------------------------------
    def score_importance(self, text: str, context: str) -> float:
        """Rate how important *text* is given *context* (0.0 – 1.0).

        Falls back to 0.5 (neutral) when the LLM is unavailable.
        """
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
        """Synthesise a list of episodic memories into a single semantic fact.

        Falls back to joining the first three texts when the LLM is unavailable.
        """
        if not texts:
            return ""

        combined = "\n".join(f"- {t}" for t in texts)
        reply = self._chat(
            system=(
                "You are a knowledge consolidation agent. "
                "Given related memory episodes, synthesise them into one concise semantic fact. "
                "Reply with only the synthesised fact."
            ),
            user=f"Episodes:\n{combined}",
            max_tokens=200,
        )
        return reply or " | ".join(t[:120] for t in texts[:3])
