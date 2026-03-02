from cerebro_python.application.adapter_registry import AdapterRegistry


def test_registry_register_create_unregister():
    registry = AdapterRegistry()
    registry.register("embedder", "dummy", lambda: "ok")

    assert registry.options("embedder") == ["dummy"]
    assert registry.create("embedder", "dummy") == "ok"

    registry.unregister("embedder", "dummy")
    assert registry.options("embedder") == []
