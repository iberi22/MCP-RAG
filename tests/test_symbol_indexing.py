from __future__ import annotations

from pathlib import Path

from cerebro_python.adapters.storage.json_symbol_index import JsonSymbolIndexRepository
from cerebro_python.application.symbol_index import SymbolIndexService


def _build_service(tmp_path: Path) -> SymbolIndexService:
    repo = JsonSymbolIndexRepository(index_path=str(tmp_path / "symbol_index.json"))
    return SymbolIndexService(repository=repo)


def test_python_symbol_ids_and_seek_retrieval(tmp_path: Path):
    code = (
        "class UserService:\n"
        "    def login(self, username: str) -> bool:\n"
        "        return bool(username)\n\n"
        "def helper(value: int) -> int:\n"
        "    return value\n"
    )
    file_path = tmp_path / "src" / "main.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(code, encoding="utf-8")

    service = _build_service(tmp_path)
    symbols = service.index_file(str(file_path))

    ids = {item.symbol_id for item in symbols}
    assert any(item.endswith("src/main.py::UserService#class") for item in ids)
    login_symbol = next(item for item in ids if item.endswith("src/main.py::UserService.login#method"))
    assert any(item.endswith("src/main.py::helper#function") for item in ids)

    payload = service.get_symbol(login_symbol)
    assert payload["status"] == "success"
    assert "def login" in payload["content"]
    assert payload["byte_end"] > payload["byte_start"]


def test_outline_and_search(tmp_path: Path):
    file_path = tmp_path / "api.ts"
    file_path.write_text(
        "export class SessionService {}\n"
        "export function createSession() { return 1; }\n"
        "const login = async () => true;\n",
        encoding="utf-8",
    )
    service = _build_service(tmp_path)
    service.index_file(str(file_path))

    outline = service.get_file_outline(str(file_path))
    assert len(outline) == 3
    assert any(item["qualified_name"] == "SessionService" for item in outline)

    hits = service.search_symbols("createSession")
    assert len(hits) >= 1
    assert hits[0]["qualified_name"] == "createSession"


def test_cross_language_extraction_minimum(tmp_path: Path):
    samples = {
        "mod.go": (
            "package main\n"
            "type UserService struct {}\n"
            "func (s *UserService) Login() bool { return true }\n"
            "func helper() {}\n",
            {"UserService#type", "UserService.Login#method", "helper#function"},
        ),
        "lib.rs": (
            "pub struct Store {}\n"
            "impl Store {\n"
            "    pub fn save(&self) {}\n"
            "}\n"
            "pub fn helper() {}\n",
            {"Store#struct", "Store.save#method", "helper#function"},
        ),
        "svc.js": (
            "class AuthService {}\n"
            "function login() { return true; }\n",
            {"AuthService#class", "login#function"},
        ),
    }

    service = _build_service(tmp_path)
    for name, (content, expected_suffixes) in samples.items():
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        symbols = service.index_file(str(path))
        suffixes = {symbol.symbol_id.split("::", 1)[1] for symbol in symbols}
        for expected in expected_suffixes:
            assert expected in suffixes


def test_symbol_file_deleted_returns_error(tmp_path: Path):
    path = tmp_path / "temp.py"
    path.write_text("def run():\n    return 1\n", encoding="utf-8")
    service = _build_service(tmp_path)
    symbols = service.index_file(str(path))
    symbol_id = symbols[0].symbol_id
    path.unlink()

    result = service.get_symbol(symbol_id)
    assert result["status"] == "error"
    assert result["error"] == "file_not_found"
