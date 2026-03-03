"""JSON-backed symbol index repository."""

from __future__ import annotations

import json
from pathlib import Path

from cerebro_python.domain.symbol_index import SymbolRecord


class JsonSymbolIndexRepository:
    def __init__(self, index_path: str = ".gitcore/symbol_index.json") -> None:
        self._index_path = Path(index_path)
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    def replace_file(self, file_path: str, symbols: list[SymbolRecord]) -> int:
        payload = self._load()
        normalized = _normalize_path(file_path)
        records: dict[str, dict] = payload.get("records", {})
        to_delete = [sid for sid, row in records.items() if row.get("file_path") == normalized]
        for sid in to_delete:
            records.pop(sid, None)
        for symbol in symbols:
            records[symbol.symbol_id] = _to_dict(symbol)
        payload["records"] = records
        self._save(payload)
        return len(symbols)

    def get(self, symbol_id: str) -> SymbolRecord | None:
        payload = self._load()
        row = payload.get("records", {}).get(symbol_id)
        if not row:
            return None
        return _from_dict(row)

    def list_file(self, file_path: str) -> list[SymbolRecord]:
        normalized = _normalize_path(file_path)
        payload = self._load()
        rows = payload.get("records", {}).values()
        out = [_from_dict(row) for row in rows if row.get("file_path") == normalized]
        out.sort(key=lambda item: (item.byte_start, item.symbol_id))
        return out

    def search(self, query: str, limit: int = 20) -> list[SymbolRecord]:
        q = query.strip().lower()
        if not q:
            return []
        payload = self._load()
        scored: list[tuple[int, SymbolRecord]] = []
        for row in payload.get("records", {}).values():
            symbol = _from_dict(row)
            sid = symbol.symbol_id.lower()
            qname = symbol.qualified_name.lower()
            sig = symbol.signature.lower()
            score = 0
            if q == qname or q == symbol.symbol_id.lower():
                score += 100
            if q in qname:
                score += 40
            if q in sid:
                score += 20
            if q in sig:
                score += 10
            if score > 0:
                scored.append((score, symbol))
        scored.sort(key=lambda item: (-item[0], item[1].symbol_id))
        return [symbol for _, symbol in scored[: max(1, limit)]]

    def _load(self) -> dict:
        return _read_payload(self._index_path)

    def _save(self, payload: dict) -> None:
        _write_payload(self._index_path, payload)


def _normalize_path(file_path: str) -> str:
    return file_path.replace("\\", "/")


def _to_dict(symbol: SymbolRecord) -> dict:
    return {
        "symbol_id": symbol.symbol_id,
        "file_path": symbol.file_path,
        "qualified_name": symbol.qualified_name,
        "kind": symbol.kind,
        "language": symbol.language,
        "byte_start": symbol.byte_start,
        "byte_end": symbol.byte_end,
        "signature": symbol.signature,
    }


def _from_dict(row: dict) -> SymbolRecord:
    return SymbolRecord(
        symbol_id=str(row["symbol_id"]),
        file_path=str(row["file_path"]),
        qualified_name=str(row["qualified_name"]),
        kind=str(row["kind"]),
        language=str(row["language"]),
        byte_start=int(row["byte_start"]),
        byte_end=int(row["byte_end"]),
        signature=str(row.get("signature", "")),
    )


def _default_payload() -> dict:
    return {"version": 1, "records": {}}


def _safe_load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _safe_parse_json(raw: str) -> dict:
    if not raw.strip():
        return _default_payload()
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return _default_payload()
        if "records" not in parsed or not isinstance(parsed["records"], dict):
            parsed["records"] = {}
        parsed.setdefault("version", 1)
        return parsed
    except json.JSONDecodeError:
        return _default_payload()


def _safe_dump_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _read_payload(path: Path) -> dict:
    return _safe_parse_json(_safe_load_text(path))


def _write_payload(path: Path, payload: dict) -> None:
    path.write_text(_safe_dump_json(payload), encoding="utf-8")

