from cerebro_python.application.agent_memory_ops import build_memory_ops_plan, detect_intent


def test_detect_intent_refresh_repo_context():
    out = detect_intent("actualiza y sync del repositorio para traer latest contexto")
    assert out.intent == "refresh_repo_context"
    assert 0.5 <= out.confidence <= 0.95


def test_detect_intent_historical_root_cause():
    out = detect_intent("cuando se introdujo esta regresion y que commit la causo")
    assert out.intent == "historical_root_cause"


def test_build_plan_cross_stack_uses_custom_scope():
    plan = build_memory_ops_plan(
        query="investiga el flujo cross stack python y rust",
        project_id="alpha",
        environment_id="dev",
        include_environment_ids=["prod"],
    )
    assert plan["intent"] == "cross_stack_investigation"
    assert any("--scope-mode custom" in step["command"] for step in plan["cli_steps"])
    assert plan["mcp_steps"][0]["args"]["scope_mode"] == "custom"


def test_build_plan_default_quick_context():
    plan = build_memory_ops_plan(
        query="donde esta la logica de scoring",
        project_id="alpha",
        environment_id="dev",
    )
    assert plan["intent"] in {"quick_context_lookup", "historical_root_cause"}
    assert plan["status"] == "success"
    assert len(plan["cli_steps"]) >= 1
