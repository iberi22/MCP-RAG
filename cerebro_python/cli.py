"""Hexagonal CLI entrypoint."""

from __future__ import annotations

from cerebro_python.adapters.cli.commands import run_cli
from cerebro_python.application.cognitive_runtime import build_cognitive_runtime_from_env
from cerebro_python.application.repo_context_sync import trigger_auto_index
from cerebro_python.bootstrap.container import Container
from cerebro_python.mcp_server_integrated import main as mcp_main


def main(argv: list[str] | None = None) -> int:
    container = Container()
    service = container.build_service()
    symbol_service = container.build_symbol_index_service()
    trigger_auto_index(service)
    cognitive_runtime = build_cognitive_runtime_from_env()
    if cognitive_runtime is not None:
        cognitive_runtime.start()

    try:
        return run_cli(
            service=service,
            launch_mcp=mcp_main,
            adapter_info=lambda: {
                "selected": container.selected_adapters(),
                "available": container.available_adapters(),
            },
            symbol_service=symbol_service,
            argv=argv,
        )
    finally:
        if cognitive_runtime is not None:
            cognitive_runtime.stop()


if __name__ == "__main__":
    raise SystemExit(main())
