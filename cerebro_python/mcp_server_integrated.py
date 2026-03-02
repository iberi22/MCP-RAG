"""Hexagonal MCP server entrypoint."""

from __future__ import annotations

import argparse

import uvicorn

from cerebro_python.bootstrap.container import Container

container = Container()
mcp = container.build_mcp()
app = mcp.streamable_http_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cerebro_python.mcp_server_integrated")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args(argv)

    if args.mode == "http":
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0

    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
