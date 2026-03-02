"""Incremental GitHub repository sync into RAG storage."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
import threading
from urllib.parse import urlparse

from cerebro_python.application.use_cases import RagService

DEFAULT_STATE_PATH = Path(".gitcore/repo_context_state.json")
DEFAULT_CACHE_DIR = Path(".cache/repo-context-repos")
DEFAULT_CONFIG_PATH = Path("scripts/skills/repo_context_sync/repos.config.json")
DEFAULT_MAX_FILE_BYTES = 300_000

DEFAULT_INCLUDE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".scala",
    ".sql",
    ".sh",
    ".bash",
    ".ps1",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".ini",
    ".cfg",
    ".xml",
    ".env",
    ".md",
}

DEFAULT_INCLUDE_FILENAMES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
}

DEFAULT_EXCLUDE_GLOBS = [
    ".git/**",
    ".svn/**",
    ".hg/**",
    "node_modules/**",
    ".venv/**",
    "venv/**",
    "__pycache__/**",
    ".mypy_cache/**",
    ".pytest_cache/**",
    ".next/**",
    ".nuxt/**",
    "dist/**",
    "build/**",
    "target/**",
    "vendor/**",
    "*.min.js",
    "*.min.css",
    "*.map",
]

DEFAULT_BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".jar",
    ".class",
    ".o",
    ".obj",
    ".pyc",
    ".pyd",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".mp3",
    ".wav",
    ".mp4",
    ".mov",
    ".avi",
    ".sqlite",
    ".db",
}

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "bash",
    ".ps1": "powershell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".md": "markdown",
}


@dataclass(slots=True, frozen=True)
class RepoTarget:
    key: str
    url: str
    branch: str
    stack: str
    project_id: str
    environment_id: str
    tags: list[str]
    include_extensions: set[str]
    include_filenames: set[str]
    exclude_globs: list[str]
    max_file_bytes: int


def parse_name_status_line(line: str) -> tuple[str, str, str]:
    """Parse a `git diff --name-status` line into status, old_path, new_path."""
    parts = line.rstrip("\n").split("\t")
    if not parts:
        return "", "", ""
    status = parts[0].strip()
    kind = status[0] if status else ""
    if kind in {"R", "C"} and len(parts) >= 3:
        return kind, _normalize_path(parts[-2]), _normalize_path(parts[-1])
    if len(parts) >= 2:
        path = _normalize_path(parts[-1])
        return kind or status, path, path
    return kind or status, "", ""


def compute_changed_paths(diff_lines: list[str]) -> tuple[set[str], set[str]]:
    """Return paths to upsert and delete from diff lines."""
    to_upsert: set[str] = set()
    to_delete: set[str] = set()
    for raw in diff_lines:
        line = raw.strip()
        if not line:
            continue
        status, old_path, new_path = parse_name_status_line(line)
        kind = status[0] if status else ""
        if kind == "D":
            if old_path:
                to_delete.add(old_path)
            continue
        if kind == "R":
            if old_path:
                to_delete.add(old_path)
            if new_path:
                to_upsert.add(new_path)
            continue
        if kind == "C":
            if new_path:
                to_upsert.add(new_path)
            continue
        if new_path:
            to_upsert.add(new_path)
    return to_upsert, to_delete


def is_allowed_path(
    path: str,
    include_extensions: set[str],
    include_filenames: set[str],
    exclude_globs: list[str],
) -> bool:
    normalized = _normalize_path(path)
    if not normalized:
        return False
    for pattern in exclude_globs:
        if fnmatch.fnmatch(normalized, pattern):
            return False
    lower_name = Path(normalized).name.lower()
    if lower_name in include_filenames:
        return True
    lower_ext = Path(normalized).suffix.lower()
    if not lower_ext:
        return False
    return lower_ext in include_extensions


def sync_repositories_from_config(
    service: RagService,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    state_path: str | Path = DEFAULT_STATE_PATH,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    full_resync: bool = False,
    dry_run: bool = False,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict[str, Any]:
    """Sync configured repositories into RAG with incremental updates."""
    config_file = Path(config_path)
    config = _load_config(config_file, fallback_max_file_bytes=max_file_bytes)
    state_file = Path(state_path)
    cache_root = Path(cache_dir)
    state = _load_state(state_file)
    repo_states = state.setdefault("repos", {})
    cache_root.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, Any]] = []
    total_upserts = 0
    total_deletes = 0
    total_skipped = 0

    for target in config:
        report = {
            "repo": target.key,
            "url": target.url,
            "branch": target.branch,
            "upserted": 0,
            "deleted": 0,
            "skipped": 0,
            "head_commit": "",
            "previous_commit": "",
            "errors": [],
        }
        try:
            repo_dir = _ensure_repo_cache(target, cache_root)
            head_commit = _git_text(repo_dir, "rev-parse", f"origin/{target.branch}").strip()
            previous_commit = str(repo_states.get(target.key, {}).get("last_commit", "")).strip()
            report["head_commit"] = head_commit
            report["previous_commit"] = previous_commit

            force_full_scan = full_resync or not previous_commit or previous_commit == head_commit
            if previous_commit and previous_commit != head_commit and not _git_commit_exists(repo_dir, previous_commit):
                force_full_scan = True

            if force_full_scan and previous_commit == head_commit and not full_resync:
                reports.append(report)
                continue

            if force_full_scan:
                upsert_paths = _list_all_paths(repo_dir, ref=f"origin/{target.branch}")
                delete_paths: set[str] = set()
            else:
                diff_lines = _git_text(
                    repo_dir,
                    "diff",
                    "--name-status",
                    "--find-renames",
                    previous_commit,
                    head_commit,
                ).splitlines()
                upsert_paths, delete_paths = compute_changed_paths(diff_lines)

            upsert_candidates = {
                p
                for p in upsert_paths
                if is_allowed_path(
                    p,
                    include_extensions=target.include_extensions,
                    include_filenames=target.include_filenames,
                    exclude_globs=target.exclude_globs,
                )
            }
            delete_candidates = {
                p
                for p in delete_paths
                if is_allowed_path(
                    p,
                    include_extensions=target.include_extensions,
                    include_filenames=target.include_filenames,
                    exclude_globs=target.exclude_globs,
                )
            }

            commit_time = _git_text(repo_dir, "show", "-s", "--format=%cI", head_commit).strip()
            for path in sorted(delete_candidates):
                report["deleted"] += 1
                total_deletes += 1
                if dry_run:
                    continue
                service.delete(document_id=build_document_id(target.key, path))

            for path in sorted(upsert_candidates):
                blob_text = _read_blob_text(repo_dir, f"origin/{target.branch}", path, max_bytes=target.max_file_bytes)
                if blob_text is None:
                    report["skipped"] += 1
                    total_skipped += 1
                    continue
                report["upserted"] += 1
                total_upserts += 1
                if dry_run:
                    continue

                language = detect_language(path)
                metadata = {
                    "source": "github-repo-context-sync",
                    "title": f"{target.key}:{path}",
                    "tags": sorted(set(target.tags + [target.stack, language, "github", "repo-sync"])),
                    "project_id": target.project_id,
                    "environment_id": target.environment_id,
                    "session_id": f"repo-sync-{datetime.now(timezone.utc).date().isoformat()}",
                    "repo_url": target.url,
                    "repo_key": target.key,
                    "repo_branch": target.branch,
                    "repo_commit": head_commit,
                    "repo_path": path,
                    "repo_stack": target.stack,
                    "event_time": commit_time,
                    "fact_key": f"repo:{target.key}:path:{path}",
                    "active": True,
                }
                payload = _format_document_payload(
                    repo_key=target.key,
                    repo_url=target.url,
                    branch=target.branch,
                    commit=head_commit,
                    path=path,
                    stack=target.stack,
                    language=language,
                    content=blob_text,
                )
                service.ingest(
                    document_id=build_document_id(target.key, path),
                    text=payload,
                    metadata=metadata,
                )

            if not dry_run:
                repo_states[target.key] = {
                    "last_commit": head_commit,
                    "last_sync_at": datetime.now(timezone.utc).isoformat(),
                    "project_id": target.project_id,
                    "environment_id": target.environment_id,
                }
        except Exception as exc:  # pragma: no cover - defensive execution
            report["errors"].append(str(exc))
        reports.append(report)

    if not dry_run:
        state["version"] = 1
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_state(state_file, state)

    return {
        "status": "success",
        "repos": reports,
        "totals": {
            "repositories": len(reports),
            "upserted": total_upserts,
            "deleted": total_deletes,
            "skipped": total_skipped,
            "dry_run": dry_run,
        },
    }


def build_document_id(repo_key: str, path: str) -> str:
    normalized_key = repo_key.replace("/", "__").replace("\\", "__")
    normalized_path = _normalize_path(path)
    digest = hashlib.sha1(f"{repo_key}:{normalized_path}".encode("utf-8")).hexdigest()[:16]
    return f"gh::{normalized_key}::{digest}"


def detect_language(path: str) -> str:
    normalized = _normalize_path(path)
    filename = Path(normalized).name.lower()
    if filename == "dockerfile":
        return "docker"
    return LANGUAGE_BY_EXTENSION.get(Path(normalized).suffix.lower(), "text")


def _format_document_payload(
    repo_key: str,
    repo_url: str,
    branch: str,
    commit: str,
    path: str,
    stack: str,
    language: str,
    content: str,
) -> str:
    return (
        f"repository: {repo_key}\n"
        f"repo_url: {repo_url}\n"
        f"branch: {branch}\n"
        f"commit: {commit}\n"
        f"path: {path}\n"
        f"stack: {stack}\n"
        f"language: {language}\n\n"
        f"{content}"
    )


def _load_config(path: Path, fallback_max_file_bytes: int) -> list[RepoTarget]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    defaults = raw.get("defaults", {})
    default_project_id = str(defaults.get("project_id", "github-repos")).strip() or "github-repos"
    default_environment_id = str(defaults.get("environment_id", "prod")).strip() or "prod"
    default_tags = [str(tag) for tag in defaults.get("tags", [])]
    default_include_extensions = {
        ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        for ext in defaults.get("include_extensions", sorted(DEFAULT_INCLUDE_EXTENSIONS))
    }
    default_include_filenames = {
        str(name).strip().lower()
        for name in defaults.get("include_filenames", sorted(DEFAULT_INCLUDE_FILENAMES))
        if str(name).strip()
    }
    default_exclude_globs = [str(p) for p in defaults.get("exclude_globs", DEFAULT_EXCLUDE_GLOBS)]
    default_max_file_bytes = int(defaults.get("max_file_bytes", fallback_max_file_bytes))

    repos: list[RepoTarget] = []
    for index, item in enumerate(raw.get("repositories", []), start=1):
        url = str(item.get("url", "")).strip()
        if not url:
            raise ValueError(f"Repository entry #{index} is missing 'url'")
        key = str(item.get("key", "")).strip() or infer_repo_key(url)
        include_extensions = {
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in item.get("include_extensions", sorted(default_include_extensions))
        }
        include_filenames = {
            str(name).strip().lower()
            for name in item.get("include_filenames", sorted(default_include_filenames))
            if str(name).strip()
        }
        exclude_globs = [str(p) for p in item.get("exclude_globs", default_exclude_globs)]
        tags = [str(tag).strip() for tag in item.get("tags", default_tags) if str(tag).strip()]
        repos.append(
            RepoTarget(
                key=key,
                url=url,
                branch=str(item.get("branch", "main")).strip() or "main",
                stack=str(item.get("stack", "generic")).strip() or "generic",
                project_id=str(item.get("project_id", default_project_id)).strip() or default_project_id,
                environment_id=str(item.get("environment_id", default_environment_id)).strip() or default_environment_id,
                tags=tags,
                include_extensions=include_extensions or set(DEFAULT_INCLUDE_EXTENSIONS),
                include_filenames=include_filenames or set(DEFAULT_INCLUDE_FILENAMES),
                exclude_globs=exclude_globs,
                max_file_bytes=int(item.get("max_file_bytes", default_max_file_bytes)),
            )
        )
    return repos


def infer_repo_key(url: str) -> str:
    source = url.strip()
    if source.startswith("git@"):
        path = source.split(":", maxsplit=1)[-1]
    else:
        path = urlparse(source).path
    cleaned = path.removesuffix(".git").strip("/")
    if not cleaned:
        raise ValueError(f"Cannot infer repository key from URL: {url}")
    return cleaned


def _ensure_repo_cache(target: RepoTarget, cache_root: Path) -> Path:
    repo_slug = target.key.replace("/", "__")
    repo_dir = cache_root / repo_slug
    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            _git_text(
                cache_root,
                "clone",
                "--no-checkout",
                "--filter=blob:none",
                "--quiet",
                "--branch",
                target.branch,
                "--single-branch",
                target.url,
                str(repo_dir),
                use_cwd=False,
            )
        except RuntimeError:
            _git_text(
                cache_root,
                "clone",
                "--no-checkout",
                "--quiet",
                "--branch",
                target.branch,
                "--single-branch",
                target.url,
                str(repo_dir),
                use_cwd=False,
            )
    _git_text(repo_dir, "fetch", "origin", target.branch, "--quiet")
    return repo_dir


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "repos": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_all_paths(repo_dir: Path, ref: str) -> set[str]:
    output = _git_text(repo_dir, "ls-tree", "-r", "--name-only", ref)
    return {_normalize_path(line) for line in output.splitlines() if line.strip()}


def _git_commit_exists(repo_dir: Path, commit: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _read_blob_text(repo_dir: Path, ref: str, path: str, max_bytes: int) -> str | None:
    normalized = _normalize_path(path)
    if Path(normalized).suffix.lower() in DEFAULT_BINARY_EXTENSIONS:
        return None
    size_output = _git_text(repo_dir, "cat-file", "-s", f"{ref}:{normalized}")
    size = int(size_output.strip() or "0")
    if size > max_bytes:
        return None
    proc = subprocess.run(
        ["git", "show", f"{ref}:{normalized}"],
        cwd=repo_dir,
        capture_output=True,
        text=False,
        check=False,
    )
    if proc.returncode != 0:
        return None
    if b"\x00" in proc.stdout:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


def _git_text(repo_dir: Path, *args: str, use_cwd: bool = True) -> str:
    cwd = repo_dir if use_cwd else None
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def trigger_auto_index(service: RagService) -> None:
    """Trigger the auto code index sync via a background thread if enabled."""
    if os.getenv("RAG_AUTO_INDEX_CODE", "false").lower() != "true":
        return

    def _sync_task() -> None:
        try:
            print("[Auto-Index] Starting repository synchronization...")
            result = sync_repositories_from_config(service=service)
            totals = result.get("totals", {})
            print(
                f"[Auto-Index] Completed. Upserts: {totals.get('upserted', 0)}, "
                f"Deletes: {totals.get('deleted', 0)}."
            )
        except Exception as e:
            print(f"[Auto-Index] Failed to synchronize repositories: {e}")

    # Fire and forget
    thread = threading.Thread(target=_sync_task, daemon=True)
    thread.start()

