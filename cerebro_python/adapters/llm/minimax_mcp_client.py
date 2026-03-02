"""MiniMax Coding Plan MCP client — wraps web_search and understand_image tools.

Spawns `uvx minimax-coding-plan-mcp` as a subprocess and communicates
with it over stdin/stdout using the MCP JSON-RPC protocol.

Requires:
  - uvx installed (from `uv` package manager)
  - MINIMAX_API_KEY environment variable
  - MINIMAX_API_HOST environment variable (default: https://api.minimax.io)

Usage:
    client = MinimaxMCPClient()
    results = client.web_search("arquitecturas de memoria para LLM")
    for r in results:
        print(r["title"], r["url"])
        print(r["snippet"])
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


_DEFAULT_API_HOST = "https://api.minimax.io"


class MinimaxMCPClient:
    """Stdio MCP client for the minimax-coding-plan-mcp server."""

    def __init__(self) -> None:
        self._api_key = os.getenv("MINIMAX_API_KEY", "")
        self._api_host = os.getenv("MINIMAX_API_HOST", _DEFAULT_API_HOST)

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Spawn the MCP server, send a tool call, and return the result.

        Uses MCP JSON-RPC protocol over stdin/stdout.
        Raises RuntimeError on failure.
        """
        if not self.is_available:
            raise RuntimeError("MINIMAX_API_KEY not set — cannot call MCP tools.")

        env = {
            **os.environ,
            "MINIMAX_API_KEY": self._api_key,
            "MINIMAX_API_HOST": self._api_host,
        }

        # Build the MCP initialize + tools/call request sequence
        initialize_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cerebro-rag", "version": "0.1"},
            },
        })
        initialized_notif = json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })
        tool_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        })

        stdin_payload = "\n".join([initialize_req, initialized_notif, tool_req]) + "\n"

        try:
            proc = subprocess.run(
                ["uvx", "minimax-coding-plan-mcp", "-y"],
                input=stdin_payload.encode("utf-8"),
                capture_output=True,
                timeout=30,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "uvx not found. Install uv first: https://docs.astral.sh/uv/"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("MCP tool call timed out after 30s") from exc

        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"minimax-coding-plan-mcp exited with error: {stderr}")

        # Parse JSON-RPC responses from stdout (one JSON object per line)
        stdout = proc.stdout.decode("utf-8", errors="replace")
        tool_result = None
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            # We want the response to request id=2 (our tools/call)
            if msg.get("id") == 2 and "result" in msg:
                tool_result = msg["result"]
                break
            if msg.get("id") == 2 and "error" in msg:
                raise RuntimeError(f"MCP tool error: {msg['error']}")

        if tool_result is None:
            raise RuntimeError(f"No tool result received. stdout={stdout[:300]}")

        return tool_result

    # ------------------------------------------------------------------
    def web_search(self, query: str) -> list[dict[str, str]]:
        """Search the web and return a list of result dicts.

        Each result has: title, url, snippet, (optionally) related_searches.
        Returns an empty list on failure (graceful degradation).
        """
        try:
            raw = self._call_tool("web_search", {"query": query})
        except RuntimeError as exc:
            print(f"[web_search] ERROR: {exc}", file=sys.stderr)
            return []

        # MCP content is a list of content blocks; we want the text block
        content = raw.get("content", [])
        text = ""
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                break

        # Try to parse as JSON array of results
        try:
            results = json.loads(text)
            if isinstance(results, list):
                return results
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: return the raw text as a single result block
        if text:
            return [{"title": query, "url": "", "snippet": text}]
        return []

    def understand_image(self, image_url: str, prompt: str = "Describe this image.") -> str:
        """Analyse an image URL and return a description string."""
        try:
            raw = self._call_tool("understand_image", {"image_url": image_url, "prompt": prompt})
        except RuntimeError as exc:
            print(f"[understand_image] ERROR: {exc}", file=sys.stderr)
            return ""

        content = raw.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
        return ""

    # ------------------------------------------------------------------
    def web_search_as_text(self, query: str, max_results: int = 5) -> str:
        """Return web search results formatted as a single ingestion-ready text block."""
        results = self.web_search(query)[:max_results]
        if not results:
            return f"No results found for: {query}"

        lines = [f"Web search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            lines.append(f"[{i}] {title}")
            if url:
                lines.append(f"    URL: {url}")
            if snippet:
                lines.append(f"    {snippet}")
            lines.append("")
        return "\n".join(lines)
