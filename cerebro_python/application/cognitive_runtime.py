"""Background runtime for periodic cognitive maintenance tasks."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import threading
import time

from cerebro_python.adapters.cognitive.memory_scorer import LocalCognitiveScorer
from cerebro_python.adapters.llm.minimax_client import MinimaxLLMClient
from cerebro_python.adapters.storage.sqlite_cognitive_repository import SqliteCognitiveRepository
from cerebro_python.adapters.storage.sqlite_repository import SqliteMemoryRepository
from cerebro_python.application.cognitive_service import CognitiveService
from cerebro_python.domain.models import CognitiveConfig


class CognitiveRuntime:
    """Runs decay and consolidation on periodic intervals."""

    def __init__(
        self,
        service: CognitiveService,
        consolidation_interval_min: int = 10,
        decay_interval_min: int = 60,
    ) -> None:
        self._service = service
        self._consolidation_interval_sec = max(60, consolidation_interval_min * 60)
        self._decay_interval_sec = max(60, decay_interval_min * 60)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout_sec: float = 2.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_sec)

    def tick(self, now: datetime | None = None) -> dict[str, int]:
        at = now or datetime.now(timezone.utc)
        forgotten = self._service.run_decay()
        consolidated = self._service.run_consolidation()
        return {
            "timestamp": int(at.timestamp()),
            "forgotten": forgotten,
            "consolidated": consolidated,
        }

    def _run_loop(self) -> None:
        last_decay = 0.0
        last_consolidation = 0.0
        while not self._stop.is_set():
            now = time.time()
            if now - last_decay >= self._decay_interval_sec:
                self._service.run_decay()
                last_decay = now
            if now - last_consolidation >= self._consolidation_interval_sec:
                self._service.run_consolidation()
                last_consolidation = now
            self._stop.wait(timeout=1.0)


def build_cognitive_runtime_from_env() -> CognitiveRuntime | None:
    """Build runtime from env vars, or return None if cognitive mode is disabled."""
    cfg = CognitiveConfig.from_env()
    if not cfg.enabled:
        return None
    if os.getenv("RAG_COGNITIVE_BACKGROUND_ENABLED", "true").lower() != "true":
        return None

    db_path = os.getenv("RAG_DB_PATH", "cerebro_rag.db")
    level_repo = SqliteCognitiveRepository(db_path=db_path)
    memory_repo = SqliteMemoryRepository(db_path=db_path)
    scorer = LocalCognitiveScorer(cfg)
    llm = MinimaxLLMClient()
    service = CognitiveService(
        level_repo=level_repo,
        scorer=scorer,
        llm=llm,
        config=cfg,
        memory_repo=memory_repo,
    )
    return CognitiveRuntime(
        service=service,
        consolidation_interval_min=int(os.getenv("RAG_COGNITIVE_CONSOLIDATION_INTERVAL_MIN", "10")),
        decay_interval_min=int(os.getenv("RAG_COGNITIVE_DECAY_INTERVAL_MIN", "60")),
    )
