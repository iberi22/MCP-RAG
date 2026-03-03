from starlette.testclient import TestClient

from cerebro_python.mcp_server_integrated import build_http_app


def test_integrated_http_exposes_health_endpoints():
    _, _, _, app = build_http_app()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "cerebro-rag"
    assert payload["transport"] == "streamable_http"

    healthz = client.get("/healthz")
    assert healthz.status_code == 200
    assert healthz.json()["status"] == "ok"


def test_integrated_http_keeps_mcp_route_available():
    _, _, _, app = build_http_app()
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/mcp" in paths
