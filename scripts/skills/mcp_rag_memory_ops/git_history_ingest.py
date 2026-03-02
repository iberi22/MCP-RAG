"""Ingest git history into RAG as process-memory documents."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cerebro_python.bootstrap.container import Container

HEADER_RE = re.compile(r"^[0-9a-f]{40}\t")


def _run_git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def parse_git_log(log_text: str) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in log_text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if HEADER_RE.match(line):
            if current is not None:
                commits.append(current)
            parts = line.split("\t", 2)
            current = {
                "hash": parts[0],
                "date": parts[1] if len(parts) > 1 else "",
                "subject": parts[2] if len(parts) > 2 else "",
                "files": [],
            }
            continue
        if current is not None:
            current["files"].append(line.strip())
    if current is not None:
        commits.append(current)
    return commits


def _format_commit_text(repo_url: str, repo_key: str, commit: dict[str, Any]) -> str:
    files = "\n".join(commit.get("files", [])) or "(no files)"
    return (
        f"repository: {repo_key}\n"
        f"repo_url: {repo_url}\n"
        f"commit: {commit.get('hash', '')}\n"
        f"date: {commit.get('date', '')}\n"
        f"subject: {commit.get('subject', '')}\n"
        f"files:\n{files}\n"
    )


def ingest_git_history(
    max_commits: int,
    project_id: str,
    environment_id: str,
    repo_key: str | None = None,
) -> dict[str, Any]:
    resolved_repo_key = repo_key or Path.cwd().name.lower()
    repo_url = _run_git("config", "--get", "remote.origin.url").strip() or f"file:///{Path.cwd()}"
    raw_log = _run_git(
        "log",
        "--date=iso-strict",
        f"--max-count={max_commits}",
        "--pretty=format:%H%x09%aI%x09%s",
        "--name-status",
    )
    commits = parse_git_log(raw_log)
    container = Container()
    service = container.build_service()

    ingested = 0
    for commit in commits:
        commit_hash = str(commit.get("hash", "")).strip()
        if not commit_hash:
            continue
        text = _format_commit_text(repo_url=repo_url, repo_key=resolved_repo_key, commit=commit)
        metadata = {
            "source": "git-history-ingest",
            "title": f"{resolved_repo_key}:{commit_hash[:12]}",
            "tags": ["git", "history", "process-memory", "codebase"],
            "project_id": project_id,
            "environment_id": environment_id,
            "session_id": "git-history-sync",
            "repo_url": repo_url,
            "repo_key": resolved_repo_key,
            "repo_commit": commit_hash,
            "event_time": commit.get("date", ""),
            "fact_key": f"git:{resolved_repo_key}:commit:{commit_hash}",
            "active": True,
        }
        service.ingest(
            document_id=f"git::{resolved_repo_key}::{commit_hash[:16]}",
            text=text,
            metadata=metadata,
        )
        ingested += 1

    return {
        "status": "success",
        "repo_key": resolved_repo_key,
        "repo_url": repo_url,
        "requested_commits": max_commits,
        "ingested_commits": ingested,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="git_history_ingest")
    parser.add_argument("--max-commits", type=int, default=80)
    parser.add_argument("--project-id", default="git-history")
    parser.add_argument("--environment-id", default="dev")
    parser.add_argument("--repo-key")
    args = parser.parse_args()

    payload = ingest_git_history(
        max_commits=max(1, args.max_commits),
        project_id=args.project_id,
        environment_id=args.environment_id,
        repo_key=args.repo_key,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
