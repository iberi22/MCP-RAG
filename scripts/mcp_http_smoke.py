"""Minimal MCP HTTP smoke check for Streamable HTTP endpoint."""

from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(prog="mcp_http_smoke")
    parser.add_argument("--url", default="http://localhost:8001/mcp")
    args = parser.parse_args()

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "mcp-http-smoke", "version": "0.1"},
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        args.url,
        method="POST",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    ok = '"result"' in body and "protocolVersion" in body
    print(json.dumps({"status": "success" if ok else "failed", "endpoint": args.url, "ok": ok}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

