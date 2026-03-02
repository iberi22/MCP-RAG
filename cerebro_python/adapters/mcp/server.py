"""FastMCP adapter."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from cerebro_python.application.use_cases import RagService


def build_mcp(service: RagService) -> FastMCP:
    mcp = FastMCP("cerebro-rag")

    @mcp.tool()
    def rag_ingest(
        document_id: str,
        text: str,
        source: str = "cli",
        title: str = "",
        tags: list[str] | None = None,
        project_id: str = "",
        environment_id: str = "",
        session_id: str = "",
    ) -> dict[str, Any]:
        return service.ingest(
            document_id=document_id,
            text=text,
            metadata={
                "source": source,
                "title": title,
                "tags": tags or [],
                "project_id": project_id,
                "environment_id": environment_id,
                "session_id": session_id,
            },
        )

    @mcp.tool()
    def rag_search(
        query: str,
        top_k: int = 5,
        min_score: float | None = None,
        project_id: str | None = None,
        environment_id: str | None = None,
        include_environment_ids: list[str] | None = None,
        scope_mode: str = "strict",
        event_time_at: str | None = None,
        ingested_before: str | None = None,
        include_inactive: bool = False,
        prefer_latest_facts: bool = True,
    ) -> dict[str, Any]:
        hits = service.search_scoped(
            query=query,
            top_k=top_k,
            min_score=min_score,
            project_id=project_id,
            environment_id=environment_id,
            include_environment_ids=include_environment_ids,
            scope_mode=scope_mode,
            event_time_at=event_time_at,
            ingested_before=ingested_before,
            include_inactive=include_inactive,
            prefer_latest_facts=prefer_latest_facts,
        )
        return {
            "status": "success",
            "query": query,
            "count": len(hits),
            "results": [
                {
                    "document_id": h.document_id,
                    "chunk_index": h.chunk_index,
                    "chunk_text": h.chunk_text,
                    "score": round(h.score, 6),
                    "metadata": h.metadata,
                }
                for h in hits
            ],
        }

    @mcp.tool()
    def rag_delete(document_id: str) -> dict[str, Any]:
        return service.delete(document_id=document_id)

    @mcp.tool()
    def rag_stats() -> dict[str, Any]:
        return service.stats()

    @mcp.tool()
    def get_server_info() -> dict[str, Any]:
        return {
            "name": "cerebro-rag",
            "architecture": "hexagonal",
            "transport": "stdio/http",
            "tools": ["rag_ingest", "rag_search", "rag_delete", "rag_stats", "get_server_info"],
        }

    return mcp
