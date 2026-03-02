"""Adapter registry for connect/disconnect of implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AdapterRegistry:
    _providers: dict[str, dict[str, Callable[[], Any]]] = field(default_factory=dict)

    def register(self, category: str, name: str, factory: Callable[[], Any]) -> None:
        self._providers.setdefault(category, {})[name] = factory

    def unregister(self, category: str, name: str) -> None:
        providers = self._providers.get(category)
        if not providers:
            return
        providers.pop(name, None)

    def create(self, category: str, name: str) -> Any:
        providers = self._providers.get(category, {})
        if name not in providers:
            known = ", ".join(sorted(providers))
            raise ValueError(f"adapter_not_found: {category}/{name}. available={known}")
        return providers[name]()

    def options(self, category: str) -> list[str]:
        return sorted(self._providers.get(category, {}))
