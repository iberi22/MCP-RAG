from cerebro_python.application.repo_context_sync import (
    _resolve_config_path,
    compute_changed_paths,
    infer_repo_key,
    is_allowed_path,
    parse_name_status_line,
)


def test_parse_name_status_line_for_rename():
    status, old_path, new_path = parse_name_status_line("R100\tsrc/old_name.py\tsrc/new_name.py")
    assert status == "R"
    assert old_path == "src/old_name.py"
    assert new_path == "src/new_name.py"


def test_compute_changed_paths_handles_add_modify_delete_and_rename():
    upserts, deletes = compute_changed_paths(
        [
            "A\tsrc/new_file.py",
            "M\tsrc/changed.py",
            "D\tsrc/removed.py",
            "R098\tsrc/old.py\tsrc/new.py",
        ]
    )
    assert upserts == {"src/new_file.py", "src/changed.py", "src/new.py"}
    assert deletes == {"src/removed.py", "src/old.py"}


def test_is_allowed_path_respects_include_and_exclude():
    include_extensions = {".py", ".ts"}
    include_filenames = {"dockerfile"}
    exclude_globs = ["node_modules/**", "dist/**", "*.min.js"]

    assert is_allowed_path("src/main.py", include_extensions, include_filenames, exclude_globs) is True
    assert is_allowed_path("Dockerfile", include_extensions, include_filenames, exclude_globs) is True
    assert is_allowed_path("dist/app.js", include_extensions, include_filenames, exclude_globs) is False
    assert is_allowed_path("node_modules/pkg/index.ts", include_extensions, include_filenames, exclude_globs) is False
    assert is_allowed_path("src/app.min.js", include_extensions, include_filenames, exclude_globs) is False
    assert is_allowed_path("src/image.png", include_extensions, include_filenames, exclude_globs) is False


def test_infer_repo_key_supports_https_and_ssh_urls():
    assert infer_repo_key("https://github.com/org/repo.git") == "org/repo"
    assert infer_repo_key("git@github.com:org/repo.git") == "org/repo"


def test_resolve_config_path_returns_existing_input(tmp_path):
    cfg = tmp_path / "repos.json"
    cfg.write_text("{}", encoding="utf-8")
    assert _resolve_config_path(cfg) == cfg


def test_resolve_config_path_uses_legacy_when_default_missing(monkeypatch, tmp_path):
    default_cfg = tmp_path / ".agents" / "skills" / "mcp_rag_memory_ops" / "repos.config.json"
    legacy_cfg = tmp_path / "scripts" / "skills" / "repo_context_sync" / "repos.config.json"
    legacy_cfg.parent.mkdir(parents=True, exist_ok=True)
    legacy_cfg.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("cerebro_python.application.repo_context_sync.DEFAULT_CONFIG_PATH", default_cfg)
    monkeypatch.setattr("cerebro_python.application.repo_context_sync.LEGACY_CONFIG_PATH", legacy_cfg)

    assert _resolve_config_path(default_cfg) == legacy_cfg


def test_resolve_config_path_raises_when_missing(monkeypatch, tmp_path):
    default_cfg = tmp_path / ".agents" / "skills" / "mcp_rag_memory_ops" / "repos.config.json"
    legacy_cfg = tmp_path / "scripts" / "skills" / "repo_context_sync" / "repos.config.json"

    monkeypatch.setattr("cerebro_python.application.repo_context_sync.DEFAULT_CONFIG_PATH", default_cfg)
    monkeypatch.setattr("cerebro_python.application.repo_context_sync.LEGACY_CONFIG_PATH", legacy_cfg)

    try:
        _resolve_config_path(default_cfg)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError as exc:
        msg = str(exc)
        assert default_cfg.as_posix() in msg
        assert legacy_cfg.as_posix() in msg
