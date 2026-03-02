"""Ebbinghaus decay engine for L2 episodic memory.

Runs periodic decay cycles that forget chunks whose memory strength
has fallen below the configured threshold.
"""

from __future__ import annotations

from datetime import datetime, timezone

from cerebro_python.domain.models import CognitiveConfig
from cerebro_python.domain.ports import MemoryLevelPort


class EbbinghausDecayEngine:
    """Applies exponential forgetting to episodic (L2) memories."""

    def __init__(self, config: CognitiveConfig, repo: MemoryLevelPort) -> None:
        self._cfg = config
        self._repo = repo

    def run_decay_cycle(self, now: datetime | None = None) -> int:
        """Apply decay to all L2 memories.

        Returns the number of chunks that were forgotten (deleted).
        """
        if now is None:
            now = datetime.now(timezone.utc)
        return self._repo.apply_decay(
            decay_lambda=self._cfg.decay_lambda,
            forget_threshold=self._cfg.forget_threshold,
            now=now,
        )
