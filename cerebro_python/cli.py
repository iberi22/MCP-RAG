"""Hexagonal CLI entrypoint."""

from __future__ import annotations

from cerebro_python.adapters.cli.commands import run_cli
from cerebro_python.bootstrap.container import Container
from cerebro_python.mcp_server_integrated import main as mcp_main


def main(argv: list[str] | None = None) -> int:
    container = Container()
    service = container.build_service()
    return run_cli(
        service=service,
        launch_mcp=mcp_main,
        adapter_info=lambda: {
            "selected": container.selected_adapters(),
            "available": container.available_adapters(),
        },
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
