from datetime import datetime, timezone

from cerebro_python.application.cognitive_runtime import CognitiveRuntime, build_cognitive_runtime_from_env


class _MockCognitiveService:
    def __init__(self) -> None:
        self.decay_calls = 0
        self.consolidation_calls = 0

    def run_decay(self) -> int:
        self.decay_calls += 1
        return 2

    def run_consolidation(self) -> int:
        self.consolidation_calls += 1
        return 1


def test_cognitive_runtime_tick_triggers_decay_and_consolidation():
    svc = _MockCognitiveService()
    runtime = CognitiveRuntime(service=svc, consolidation_interval_min=10, decay_interval_min=60)
    result = runtime.tick(now=datetime.now(timezone.utc))
    assert svc.decay_calls == 1
    assert svc.consolidation_calls == 1
    assert result["forgotten"] == 2
    assert result["consolidated"] == 1


def test_build_cognitive_runtime_disabled(monkeypatch):
    monkeypatch.setenv("RAG_COGNITIVE_ENABLED", "false")
    assert build_cognitive_runtime_from_env() is None
