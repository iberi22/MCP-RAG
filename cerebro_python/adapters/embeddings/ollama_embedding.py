"""Ollama embedding adapter."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter


class OllamaEmbeddingAdapter:
    def __init__(self, base_url: str, model: str, timeout: float = 20.0, fallback: HashEmbeddingAdapter | None = None):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._fallback = fallback or HashEmbeddingAdapter()

    def embed(self, text: str) -> list[float]:
        payload = json.dumps({"model": self._model, "input": text}).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self._base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
            embeddings = body.get("embeddings")
            if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
                return [float(x) for x in embeddings[0]]
            embedding = body.get("embedding")
            if isinstance(embedding, list):
                return [float(x) for x in embedding]
            raise RuntimeError("ollama_invalid_response")
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError):
            return self._fallback.embed(text)
