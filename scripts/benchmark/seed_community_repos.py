"""Seed community repositories for RAG benchmarking."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

def run_git(args: list[str], cwd: Path | None = None) -> None:
    print(f"Running git {' '.join(args)}...")
    subprocess.run(["git"] + args, cwd=cwd, check=True)

def main():
    parser = argparse.ArgumentParser(description="Seed community repos for benchmarking.")
    parser.add_argument("--repos", nargs="+", required=True, help="List of GitHub repos (e.g., langchain-ai/langchain)")
    parser.add_argument("--environment-id", default="benchmark", help="Environment ID for isolated RAG indexing")
    parser.add_argument("--cache-dir", default=".cache/benchmark-repos", help="Directory to clone and index repos")
    parser.add_argument("--state-file", default=".gitcore/benchmark_state.json", help="State file for the sync command")
    args = parser.parse_args()

    cache_dir = ROOT_DIR / args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "defaults": {
            "project_id": "community-benchmarks",
            "environment_id": args.environment_id,
            "tags": ["benchmark", "community"],
            "include_extensions": [".py", ".ts", ".js", ".md"],
            "include_filenames": [],
            "exclude_globs": [".git/**", "node_modules/**", "tests/**", "docs/**"],
            "max_file_bytes": 300000
        },
        "repositories": []
    }

    for repo in args.repos:
        repo_name = repo.split("/")[-1]
        target_dir = cache_dir / repo_name
        if not target_dir.exists():
            run_git(["clone", "--depth", "1", f"https://github.com/{repo}.git", str(target_dir)])

        config["repositories"].append({
            "key": f"benchmark/{repo_name}",
            "url": f"https://github.com/{repo}",
            "branch": "main",  # Assuming main for simplicity; may need adjustment if master
            "stack": "mixed",
            "project_id": "community-benchmarks",
            "environment_id": args.environment_id,
            "tags": ["benchmark"]
        })

    # Optional: If main fails, try falling back to master if we checked it out
    for r in config["repositories"]:
        repo_dir = cache_dir / r["key"].split("/")[-1]
        try:
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo_dir, text=True).strip()
            r["branch"] = branch
        except subprocess.CalledProcessError:
            pass

    config_path = cache_dir / "benchmark-repos.config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"\nCreated config at {config_path}")
    print("\nRunning RAG sync...")

    sync_cmd = [
        "python", "-m", "cerebro_python", "rag-sync-repos",
        "--config", str(config_path),
        "--state", str(ROOT_DIR / args.state_file),
        "--cache-dir", str(cache_dir / "_sync_cache")
    ]
    print(f"Executing: {' '.join(sync_cmd)}")
    subprocess.run(sync_cmd, cwd=ROOT_DIR, check=True)
    print("Seeding complete.")

if __name__ == "__main__":
    main()
