"""Decision helpers for agent memory operations over CLI and MCP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IntentResult:
    intent: str
    confidence: float


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "refresh_repo_context": (
        "sync",
        "actualiza",
        "actualizar",
        "latest",
        "ultimo",
        "último",
        "refresh",
        "repositorio",
        "repositorios",
    ),
    "historical_root_cause": (
        "regression",
        "regresion",
        "regresión",
        "history",
        "historial",
        "commit",
        "blame",
        "cuando",
        "when",
        "por que",
        "por qué",
        "root cause",
    ),
    "cross_stack_investigation": (
        "cross",
        "across",
        "stack",
        "multi",
        "python y rust",
        "python and rust",
        "typescript y python",
    ),
    "quick_context_lookup": (
        "contexto",
        "context",
        "buscar",
        "search",
        "donde",
        "dónde",
        "where",
        "how",
        "como",
        "cómo",
        "funcion",
        "función",
    ),
}


def detect_intent(query: str) -> IntentResult:
    text = (query or "").strip().lower()
    if not text:
        return IntentResult(intent="quick_context_lookup", confidence=0.4)

    scores: dict[str, int] = {intent: 0 for intent in INTENT_KEYWORDS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[intent] += 1

    winner = max(scores, key=scores.get)
    max_score = scores[winner]
    if max_score <= 0:
        return IntentResult(intent="quick_context_lookup", confidence=0.45)

    total = sum(scores.values()) or 1
    confidence = min(0.95, 0.55 + (max_score / total) * 0.35)
    return IntentResult(intent=winner, confidence=round(confidence, 3))


def build_memory_ops_plan(
    query: str,
    top_k: int = 8,
    project_id: str | None = None,
    environment_id: str | None = None,
    include_environment_ids: list[str] | None = None,
) -> dict:
    intent = detect_intent(query)
    pid = project_id or "<project-id>"
    eid = environment_id or "<environment-id>"
    include_envs = [env for env in (include_environment_ids or []) if env]

    strict_search = (
        f'python -m cerebro_python rag-search --query "{query}" --top-k {top_k} '
        f"--project-id {pid} --environment-id {eid} --scope-mode strict"
    )
    custom_search = strict_search.replace("--scope-mode strict", "--scope-mode custom")
    if include_envs:
        includes = " ".join(f"--include-environment-id {env}" for env in include_envs)
        custom_search = f"{custom_search} {includes}"

    plan = {
        "status": "success",
        "intent": intent.intent,
        "confidence": intent.confidence,
        "query": query,
        "guardrails": [
            "default-scope-strict",
            "preserve-provenance-metadata",
            "prefer-incremental-sync",
            "avoid-unscoped-global-retrieval",
        ],
        "cli_steps": [],
        "mcp_steps": [],
    }

    if intent.intent == "refresh_repo_context":
        plan["cli_steps"] = [
            {
                "name": "sync_repositories",
                "command": (
                    "python -m cerebro_python rag-sync-repos "
                    "--config scripts/skills/repo_context_sync/repos.config.json "
                    "--state .gitcore/repo_context_state.json "
                    "--cache-dir .cache/repo-context-repos"
                ),
            },
            {"name": "query_updated_context", "command": strict_search},
        ]
        plan["mcp_steps"] = [
            {
                "tool": "rag_search",
                "args": {
                    "query": query,
                    "top_k": top_k,
                    "project_id": project_id,
                    "environment_id": environment_id,
                    "scope_mode": "strict",
                },
            }
        ]
        return plan

    if intent.intent == "historical_root_cause":
        plan["cli_steps"] = [
            {
                "name": "inspect_recent_commits",
                "command": "git log --date=iso --decorate --graph --max-count 40 --oneline",
            },
            {
                "name": "ingest_git_history_to_rag",
                "command": (
                    "python scripts/skills/mcp_rag_memory_ops/git_history_ingest.py "
                    f"--max-commits 80 --project-id {pid} --environment-id {eid}"
                ),
            },
            {"name": "search_historical_context", "command": strict_search},
        ]
        plan["mcp_steps"] = [
            {
                "tool": "rag_search",
                "args": {
                    "query": f"{query} commit regression history blame",
                    "top_k": top_k,
                    "project_id": project_id,
                    "environment_id": environment_id,
                    "scope_mode": "strict",
                },
            }
        ]
        return plan

    if intent.intent == "cross_stack_investigation":
        if not include_envs:
            include_envs = ["<other-environment-id>"]
            custom_search = f"{custom_search} --include-environment-id <other-environment-id>"
        plan["cli_steps"] = [
            {"name": "cross_scope_query", "command": custom_search},
            {
                "name": "verify_scope_isolation",
                "command": (
                    f'python -m cerebro_python rag-search --query "{query}" --top-k {top_k} '
                    f"--project-id {pid} --environment-id {eid} --scope-mode strict"
                ),
            },
        ]
        plan["mcp_steps"] = [
            {
                "tool": "rag_search",
                "args": {
                    "query": query,
                    "top_k": top_k,
                    "project_id": project_id,
                    "environment_id": environment_id,
                    "scope_mode": "custom",
                    "include_environment_ids": include_envs,
                },
            }
        ]
        return plan

    plan["cli_steps"] = [{"name": "strict_context_lookup", "command": strict_search}]
    plan["mcp_steps"] = [
        {
            "tool": "rag_search",
            "args": {
                "query": query,
                "top_k": top_k,
                "project_id": project_id,
                "environment_id": environment_id,
                "scope_mode": "strict",
            },
        }
    ]
    return plan
