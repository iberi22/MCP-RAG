"""Hexagonal MCP server entrypoint."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse

from cerebro_python.adapters.mcp.server import build_mcp
from cerebro_python.application.cognitive_runtime import build_cognitive_runtime_from_env
from cerebro_python.application.repo_context_sync import trigger_auto_index
from cerebro_python.bootstrap.container import Container


def _attach_health_routes(app: Starlette) -> None:
    async def health(_: object) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "cerebro-rag",
                "transport": "streamable_http",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    app.add_route("/health", health, methods=["GET"])
    app.add_route("/healthz", health, methods=["GET"])


def build_runtime() -> tuple[Container, object]:
    container = Container()
    service = container.build_service()
    return container, service


def build_http_app() -> tuple[Container, object, object, Starlette]:
    container, service = build_runtime()
    mcp = build_mcp(service)
    app = mcp.streamable_http_app()
    _attach_health_routes(app)
    return container, service, mcp, app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cerebro_python.mcp_server_integrated")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args(argv)

    container, service, mcp, app = build_http_app()
    trigger_auto_index(service)
    cognitive_runtime = build_cognitive_runtime_from_env()
    if cognitive_runtime is not None:
        cognitive_runtime.start()

    try:
        if args.mode == "http":
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            return 0

        mcp.run()
        return 0
    finally:
        if cognitive_runtime is not None:
            cognitive_runtime.stop()


if __name__ == "__main__":
    raise SystemExit(main())
