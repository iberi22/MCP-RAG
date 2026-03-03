from __future__ import annotations

from cerebro_python.adapters.llm.cli_agent_adapter import CLIAgentLLMClient
from cerebro_python.adapters.llm.deepseek_client import DeepSeekLLMClient
from cerebro_python.adapters.llm.minimax_client import MinimaxLLMClient
from cerebro_python.adapters.llm.openrouter_client import OpenRouterLLMClient
from cerebro_python.bootstrap.container import Container
from cerebro_python.domain.llm_provider import LLMProvider


def test_minimax_implements_provider_protocol():
    assert isinstance(MinimaxLLMClient(), LLMProvider)


def test_openrouter_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterLLMClient()
    assert client.is_available is False
    assert client.rewrite_query("auth flow") == "auth flow"


def test_openrouter_parses_structured_outputs(monkeypatch):
    client = OpenRouterLLMClient()
    monkeypatch.setattr(
        client,
        "_chat",
        lambda *args, **kwargs: '{"expanded_query":"jwt oauth session","keywords":["jwt"]}',
    )
    assert client.rewrite_query("jwt") == "jwt oauth session"

    monkeypatch.setattr(client, "_chat", lambda *args, **kwargs: "0.82")
    assert client.score_relevance("q", "candidate") == 0.82


def test_deepseek_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = DeepSeekLLMClient()
    assert client.is_available is False
    assert client.score_importance("text", "ctx") == 0.5


def test_deepseek_fallback_when_unparseable(monkeypatch):
    client = DeepSeekLLMClient()
    monkeypatch.setattr(client, "_chat", lambda *args, **kwargs: "not-a-number")
    assert client.score_relevance("query", "candidate") == 0.0
    assert client.score_importance("text", "ctx") == 0.5


def test_cli_agent_unavailable_when_binary_missing(monkeypatch):
    monkeypatch.setattr("cerebro_python.adapters.llm.cli_agent_adapter.shutil.which", lambda _: None)
    client = CLIAgentLLMClient(agent_binary="missing-binary")
    assert client.is_available is False
    assert client.rewrite_query("query") == "query"
    assert client.score_importance("text", "ctx") == 0.5
    assert client.score_relevance("q", "c") == 0.0


def test_cli_agent_handles_binary_removed_during_execution(monkeypatch):
    monkeypatch.setattr(
        "cerebro_python.adapters.llm.cli_agent_adapter.shutil.which",
        lambda _: "C:/fake/codex.exe",
    )
    client = CLIAgentLLMClient(agent_binary="codex")

    def _raise_not_found(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(
        "cerebro_python.adapters.llm.cli_agent_adapter.subprocess.run",
        _raise_not_found,
    )
    assert client.rewrite_query("my query") == "my query"
    assert client.is_available is False


def test_cli_agent_successful_score_parsing(monkeypatch):
    monkeypatch.setattr(
        "cerebro_python.adapters.llm.cli_agent_adapter.shutil.which",
        lambda _: "C:/fake/codex.exe",
    )
    client = CLIAgentLLMClient(agent_binary="codex")
    monkeypatch.setattr(client, "_run_cli", lambda prompt: "0.77")
    assert client.score_relevance("q", "c") == 0.77

    monkeypatch.setattr(client, "_run_cli", lambda prompt: "8")
    assert client.score_importance("text", "ctx") == 0.8


def test_container_selects_expected_llm_provider(monkeypatch):
    scenarios = [
        ("minimax", MinimaxLLMClient, None),
        ("openrouter", OpenRouterLLMClient, None),
        ("deepseek", DeepSeekLLMClient, None),
        ("codex", CLIAgentLLMClient, "codex"),
        ("gemini", CLIAgentLLMClient, "gemini"),
        ("qwen", CLIAgentLLMClient, "qwen"),
    ]
    for provider_name, expected_type, expected_binary in scenarios:
        monkeypatch.setenv("RAG_LLM_PROVIDER", provider_name)
        provider = Container().build_llm_provider()
        assert isinstance(provider, expected_type)
        if expected_binary is not None:
            assert provider._binary == expected_binary  # noqa: SLF001 - adapter contract assertion
