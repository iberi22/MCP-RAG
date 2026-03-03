"""Simple text chunker adapter."""

from __future__ import annotations


class SimpleChunker:
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150):
        self._chunk_size = max(200, chunk_size)
        self._chunk_overlap = max(0, min(chunk_overlap, self._chunk_size - 1))

    def split(self, text: str) -> list[str]:
        """Split text into chunks."""
        cleaned = text.strip()
        if not cleaned:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(start + self._chunk_size, len(cleaned))
            if end < len(cleaned):
                newline = cleaned.rfind("\n", start, end)
                space = cleaned.rfind(" ", start, end)
                pivot = max(newline, space)
                if pivot > start + 80:
                    end = pivot

            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= len(cleaned):
                break
            start = max(end - self._chunk_overlap, start + 1)

        return chunks

    def chunk(self, text: str) -> list[str]:
        """Alias for split() - for compatibility with other chunkers."""
        return self.split(text)
