"""AST-based chunker that calls a high-performance Rust binary (tree-sitter)."""

import json
import os
import subprocess
from pathlib import Path

from cerebro_python.adapters.chunking.simple_chunker import SimpleChunker


class AstChunker:
    """Semantic chunker using Rust + tree-sitter for high-quality RAG indexing."""

    def __init__(self, binary_path: str | None = None) -> None:
        if not binary_path:
            # Assume it's located in the tools workspace relative to the project root
            cwd = Path.cwd()
            candidate = cwd / "tools" / "rust-ast-chunker" / "target" / "release" / "rust-ast-chunker"
            if os.name == "nt":
                candidate = candidate.with_suffix(".exe")
            binary_path = str(candidate)

        self.binary_path = binary_path
        self._fallback = SimpleChunker()

    def split(self, text: str) -> list[str]:
        """Split text into chunks (alias for chunk method for CLI compatibility)."""
        return self.chunk(text)

    def chunk(self, text: str) -> list[str]:
        """Chunk raw text (e.g. from tests where no file path is given).

        Since AST chunking needs a language structure, raw text without language
        extensions falls back to SimpleChunker.
        """
        return self._fallback.chunk(text)

    def chunk_file(self, file_path: str) -> list[str]:
        """Parses a file via the Rust AST chunker. Fallback to SimpleChunker on error."""
        if not os.path.exists(self.binary_path):
            # Binary not found or not compiled
            return self._fallback.chunk(Path(file_path).read_text(encoding="utf-8"))

        try:
            result = subprocess.run(
                [self.binary_path, "--file", file_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                print(f"[AST Chunker] Failed for {file_path}, code: {result.returncode}. Fallback to simple.")
                return self._fallback.chunk(Path(file_path).read_text(encoding="utf-8"))

            # Parse JSON output
            data = json.loads(result.stdout)

            # Filter and map snippets
            chunks = []
            for item in data:
                # Add contextual headers for LLM (e.g., function name/type)
                name = item.get("name") or "anonymous"
                node_type = item.get("node_type", "block").replace("_", " ")
                snippet = item.get("snippet", "")

                header = f"[{node_type} '{name}']"
                chunks.append(f"{header}\n{snippet}")

            # If nothing useful came out (e.g., small config files with no functions), fallback
            if not chunks:
                return self._fallback.chunk(Path(file_path).read_text(encoding="utf-8"))

            return chunks

        except Exception as e:
            print(f"[AST Chunker] Error chunking {file_path}: {e}. Fallback to simple.")
            return self._fallback.chunk(Path(file_path).read_text(encoding="utf-8"))
