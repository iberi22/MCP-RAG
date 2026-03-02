from cerebro_python.adapters.scope.auto_scope_strategy import AutoScopeStrategy
from cerebro_python.adapters.scope.strict_scope_strategy import StrictScopeStrategy


def test_strict_scope_strategy_blocks_expansion_by_default():
    strategy = StrictScopeStrategy()
    out = strategy.select_additional_environments(
        query="rollback release",
        environment_id="dev",
        requested_environment_ids=["prod"],
        scope_mode="strict",
    )
    assert out == []


def test_strict_scope_strategy_allows_custom_requested_envs():
    strategy = StrictScopeStrategy()
    out = strategy.select_additional_environments(
        query="rollback release",
        environment_id="dev",
        requested_environment_ids=["prod", "stage"],
        scope_mode="custom",
    )
    assert out == ["prod", "stage"]


def test_auto_scope_strategy_adds_prod_for_release_intent():
    strategy = AutoScopeStrategy()
    out = strategy.select_additional_environments(
        query="release rollback checklist",
        environment_id="dev",
        requested_environment_ids=[],
        scope_mode="auto",
    )
    assert "prod" in out

