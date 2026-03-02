"""Auto scope strategy with lightweight intent rules."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
_PROD_INTENT = {"deploy", "deployment", "release", "rollback", "incident", "hotfix", "production", "prod"}
_DEV_INTENT = {"implement", "feature", "refactor", "test", "unit", "debug", "development", "dev"}


class AutoScopeStrategy:
    def select_additional_environments(
        self,
        query: str,
        environment_id: str | None,
        requested_environment_ids: list[str] | None,
        scope_mode: str,
    ) -> list[str]:
        requested = {env for env in (requested_environment_ids or []) if env and env != environment_id}
        if scope_mode == "strict":
            return []
        if scope_mode == "custom":
            return sorted(requested)

        tokens = set(_TOKEN_RE.findall(query.lower()))
        out = set(requested)
        if environment_id == "dev" and (tokens & _PROD_INTENT):
            out.add("prod")
        if environment_id == "prod" and (tokens & _DEV_INTENT):
            out.add("dev")
        return sorted(env for env in out if env and env != environment_id)

