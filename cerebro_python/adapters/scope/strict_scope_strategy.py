"""Strict scope strategy: no implicit cross-environment expansion."""

from __future__ import annotations


class StrictScopeStrategy:
    def select_additional_environments(
        self,
        query: str,
        environment_id: str | None,
        requested_environment_ids: list[str] | None,
        scope_mode: str,
    ) -> list[str]:
        if scope_mode == "custom":
            requested = [env for env in (requested_environment_ids or []) if env and env != environment_id]
            return sorted(set(requested))
        return []

