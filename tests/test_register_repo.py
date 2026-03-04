"""Unit tests for register_repo_in_config dedup logic."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cerebro_python.application.repo_context_sync import register_repo_in_config


@pytest.fixture()
def cfg(tmp_path: Path) -> Path:
    """Return a path to a minimal repos.config.json in a temp directory."""
    config = tmp_path / "repos.config.json"
    config.write_text(
        json.dumps({"defaults": {}, "repositories": []}),
        encoding="utf-8",
    )
    return config


def _load_repos(cfg: Path) -> list[dict]:
    return json.loads(cfg.read_text(encoding="utf-8"))["repositories"]


# ─── Happy path ──────────────────────────────────────────────────────────────

def test_register_new_repo_appends_entry(cfg: Path) -> None:
    result = register_repo_in_config(
        "https://github.com/org/my-app.git",
        config_path=cfg,
        branch="main",
        stack="typescript",
        project_id="my-app",
        environment_id="dev",
        tags=["frontend"],
    )

    assert result["status"] == "registered"
    assert result["key"] == "org/my-app"
    repos = _load_repos(cfg)
    assert len(repos) == 1
    assert repos[0]["stack"] == "typescript"
    assert "frontend" in repos[0]["tags"]


def test_register_same_url_twice_is_update(cfg: Path) -> None:
    url = "https://github.com/org/backend.git"
    register_repo_in_config(url, config_path=cfg, branch="main", stack="python")
    result = register_repo_in_config(url, config_path=cfg, branch="develop", stack="python")

    assert result["status"] == "updated"
    repos = _load_repos(cfg)
    # Must not duplicate
    assert len(repos) == 1
    assert repos[0]["branch"] == "develop"


def test_register_same_key_is_update(cfg: Path) -> None:
    register_repo_in_config(
        "https://github.com/org/svc.git",
        config_path=cfg,
        key="my-key",
        stack="go",
    )
    result = register_repo_in_config(
        "https://github.com/org/svc-renamed.git",
        config_path=cfg,
        key="my-key",
        stack="go",
    )

    assert result["status"] == "updated"
    repos = _load_repos(cfg)
    assert len(repos) == 1
    # URL should be updated to the new one
    assert repos[0]["url"] == "https://github.com/org/svc-renamed.git"


def test_different_repos_both_registered(cfg: Path) -> None:
    register_repo_in_config("https://github.com/org/a.git", config_path=cfg)
    register_repo_in_config("https://github.com/org/b.git", config_path=cfg)

    repos = _load_repos(cfg)
    assert len(repos) == 2


# ─── Key inference ───────────────────────────────────────────────────────────

def test_key_inferred_from_https_url(cfg: Path) -> None:
    result = register_repo_in_config("https://github.com/myorg/myrepo.git", config_path=cfg)
    assert result["key"] == "myorg/myrepo"


def test_key_inferred_from_ssh_url(cfg: Path) -> None:
    result = register_repo_in_config("git@github.com:myorg/myrepo.git", config_path=cfg)
    assert result["key"] == "myorg/myrepo"


def test_key_inferred_from_local_file_url(cfg: Path) -> None:
    result = register_repo_in_config(
        "file:///e:/scripts-python/MCP-RAG",
        config_path=cfg,
    )
    assert result["key"] == "e:/scripts-python/MCP-RAG"


def test_explicit_key_overrides_inferred(cfg: Path) -> None:
    result = register_repo_in_config(
        "https://github.com/org/repo.git",
        config_path=cfg,
        key="local/my-custom-key",
    )
    assert result["key"] == "local/my-custom-key"


# ─── Tags preservation ───────────────────────────────────────────────────────

def test_old_tags_preserved_when_not_supplied_on_update(cfg: Path) -> None:
    url = "https://github.com/org/tagged.git"
    register_repo_in_config(url, config_path=cfg, tags=["alpha", "beta"])
    # Update without providing tags
    register_repo_in_config(url, config_path=cfg, branch="develop")

    repos = _load_repos(cfg)
    assert repos[0]["tags"] == ["alpha", "beta"]


def test_new_tags_overwrite_on_update(cfg: Path) -> None:
    url = "https://github.com/org/tagged2.git"
    register_repo_in_config(url, config_path=cfg, tags=["old-tag"])
    register_repo_in_config(url, config_path=cfg, tags=["new-tag"])

    repos = _load_repos(cfg)
    assert repos[0]["tags"] == ["new-tag"]


# ─── Config file creation ─────────────────────────────────────────────────────

def test_creates_config_file_if_missing(tmp_path: Path) -> None:
    cfg_path = tmp_path / "subdir" / "repos.config.json"
    assert not cfg_path.exists()

    result = register_repo_in_config("https://github.com/org/new.git", config_path=cfg_path)

    assert cfg_path.exists()
    assert result["status"] == "registered"
