"""Application service for symbol extraction and byte-offset retrieval."""

from __future__ import annotations

import re
from pathlib import Path

from cerebro_python.adapters.storage.json_symbol_index import JsonSymbolIndexRepository
from cerebro_python.domain.symbol_index import SymbolRecord

_EXT_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
}


class SymbolIndexService:
    def __init__(self, repository: JsonSymbolIndexRepository | None = None) -> None:
        self._repository = repository or JsonSymbolIndexRepository()

    def index_file(self, file_path: str) -> list[SymbolRecord]:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8")
        language = _EXT_LANGUAGE.get(path.suffix.lower())
        if not language:
            self._repository.replace_file(_normalize_path(path), [])
            return []

        starts, candidates, total_bytes = _extract_candidates(text, language)
        normalized_path = _normalize_path(path)
        symbols: list[SymbolRecord] = []
        for i, candidate in enumerate(candidates):
            start_byte = starts[candidate["line_index"]]
            end_byte = starts[candidates[i + 1]["line_index"]] if i + 1 < len(candidates) else total_bytes
            kind = str(candidate["kind"])
            qualified_name = str(candidate["qualified_name"])
            symbol_id = f"{normalized_path}::{qualified_name}#{kind}"
            symbols.append(
                SymbolRecord(
                    symbol_id=symbol_id,
                    file_path=normalized_path,
                    qualified_name=qualified_name,
                    kind=kind,
                    language=language,
                    byte_start=int(start_byte),
                    byte_end=int(max(start_byte, end_byte)),
                    signature=str(candidate["signature"]),
                )
            )
        self._repository.replace_file(normalized_path, symbols)
        return symbols

    def get_symbol(self, symbol_id: str) -> dict:
        symbol = self._repository.get(symbol_id)
        if symbol is None:
            return {"status": "error", "error": "symbol_not_found", "symbol_id": symbol_id}
        path = Path(symbol.file_path)
        try:
            with path.open("rb") as handle:
                handle.seek(symbol.byte_start)
                size = max(0, symbol.byte_end - symbol.byte_start)
                content = handle.read(size).decode("utf-8", errors="replace")
        except FileNotFoundError:
            return {
                "status": "error",
                "error": "file_not_found",
                "symbol_id": symbol_id,
                "file_path": symbol.file_path,
            }
        return {
            "status": "success",
            "symbol_id": symbol.symbol_id,
            "file_path": symbol.file_path,
            "qualified_name": symbol.qualified_name,
            "kind": symbol.kind,
            "byte_start": symbol.byte_start,
            "byte_end": symbol.byte_end,
            "content": content,
        }

    def get_file_outline(self, file_path: str) -> list[dict]:
        symbols = self._repository.list_file(_normalize_path(Path(file_path)))
        return [
            {
                "symbol_id": symbol.symbol_id,
                "qualified_name": symbol.qualified_name,
                "kind": symbol.kind,
                "language": symbol.language,
                "byte_start": symbol.byte_start,
                "byte_end": symbol.byte_end,
                "signature": symbol.signature,
            }
            for symbol in symbols
        ]

    def search_symbols(self, query: str, limit: int = 20) -> list[dict]:
        hits = self._repository.search(query=query, limit=limit)
        return [
            {
                "symbol_id": symbol.symbol_id,
                "qualified_name": symbol.qualified_name,
                "kind": symbol.kind,
                "language": symbol.language,
                "file_path": symbol.file_path,
                "signature": symbol.signature,
            }
            for symbol in hits
        ]


def _normalize_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_candidates(text: str, language: str) -> tuple[list[int], list[dict], int]:
    lines = text.splitlines(keepends=True)
    starts: list[int] = []
    cursor = 0
    for line in lines:
        starts.append(cursor)
        cursor += len(line.encode("utf-8"))
    if not lines:
        return [], [], 0
    if language == "python":
        candidates = _extract_python(lines)
    elif language in {"javascript", "typescript"}:
        candidates = _extract_js_ts(lines)
    elif language == "go":
        candidates = _extract_go(lines)
    elif language == "rust":
        candidates = _extract_rust(lines)
    else:
        candidates = []
    return starts, candidates, cursor


def _extract_python(lines: list[str]) -> list[dict]:
    class_pat = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    def_pat = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    class_stack: list[tuple[int, str]] = []
    out: list[dict] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        while class_stack and indent <= class_stack[-1][0]:
            class_stack.pop()
        class_match = class_pat.match(line)
        if class_match:
            class_name = class_match.group(1)
            class_stack.append((indent, class_name))
            out.append(
                {
                    "line_index": i,
                    "qualified_name": class_name,
                    "kind": "class",
                    "signature": stripped,
                }
            )
            continue
        def_match = def_pat.match(line)
        if def_match:
            fn_name = def_match.group(1)
            if class_stack:
                qualified = f"{class_stack[-1][1]}.{fn_name}"
                kind = "method"
            else:
                qualified = fn_name
                kind = "function"
            out.append(
                {
                    "line_index": i,
                    "qualified_name": qualified,
                    "kind": kind,
                    "signature": stripped,
                }
            )
    return out


def _extract_js_ts(lines: list[str]) -> list[dict]:
    class_pat = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    fn_pat = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    arrow_pat = re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
    )
    out: list[dict] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        class_match = class_pat.match(line)
        if class_match:
            out.append(
                {
                    "line_index": i,
                    "qualified_name": class_match.group(1),
                    "kind": "class",
                    "signature": stripped,
                }
            )
            continue
        fn_match = fn_pat.match(line)
        if fn_match:
            out.append(
                {
                    "line_index": i,
                    "qualified_name": fn_match.group(1),
                    "kind": "function",
                    "signature": stripped,
                }
            )
            continue
        arrow_match = arrow_pat.match(line)
        if arrow_match:
            out.append(
                {
                    "line_index": i,
                    "qualified_name": arrow_match.group(1),
                    "kind": "function",
                    "signature": stripped,
                }
            )
    return out


def _extract_go(lines: list[str]) -> list[dict]:
    type_pat = re.compile(r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b")
    method_pat = re.compile(
        r"^\s*func\s+\(\s*[A-Za-z_][A-Za-z0-9_]*\s+\*?([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\("
    )
    fn_pat = re.compile(r"^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    out: list[dict] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        type_match = type_pat.match(line)
        if type_match:
            out.append(
                {
                    "line_index": i,
                    "qualified_name": type_match.group(1),
                    "kind": "type",
                    "signature": stripped,
                }
            )
            continue
        method_match = method_pat.match(line)
        if method_match:
            qualified = f"{method_match.group(1)}.{method_match.group(2)}"
            out.append(
                {
                    "line_index": i,
                    "qualified_name": qualified,
                    "kind": "method",
                    "signature": stripped,
                }
            )
            continue
        fn_match = fn_pat.match(line)
        if fn_match:
            out.append(
                {
                    "line_index": i,
                    "qualified_name": fn_match.group(1),
                    "kind": "function",
                    "signature": stripped,
                }
            )
    return out


def _extract_rust(lines: list[str]) -> list[dict]:
    type_pat = re.compile(r"^\s*(?:pub\s+)?(struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    fn_pat = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    impl_pat = re.compile(r"^\s*impl(?:\s+<[^\>]+>)?\s+([A-Za-z_][A-Za-z0-9_]*)")
    out: list[dict] = []
    current_impl: str | None = None
    current_impl_depth = 0
    depth = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            depth += line.count("{") - line.count("}")
            if current_impl is not None and depth < current_impl_depth:
                current_impl = None
            continue

        impl_match = impl_pat.match(line)
        if impl_match:
            current_impl = impl_match.group(1)
            current_impl_depth = depth + line.count("{")

        type_match = type_pat.match(line)
        if type_match:
            out.append(
                {
                    "line_index": i,
                    "qualified_name": type_match.group(2),
                    "kind": type_match.group(1),
                    "signature": stripped,
                }
            )
        else:
            fn_match = fn_pat.match(line)
            if fn_match:
                name = fn_match.group(1)
                if current_impl:
                    qualified = f"{current_impl}.{name}"
                    kind = "method"
                else:
                    qualified = name
                    kind = "function"
                out.append(
                    {
                        "line_index": i,
                        "qualified_name": qualified,
                        "kind": kind,
                        "signature": stripped,
                    }
                )
        depth += line.count("{") - line.count("}")
        if current_impl is not None and depth < current_impl_depth:
            current_impl = None
    return out
