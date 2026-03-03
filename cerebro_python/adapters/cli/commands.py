"""CLI adapter."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from cerebro_python.application.agent_memory_ops import build_memory_ops_plan
from cerebro_python.application.repo_context_sync import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG_PATH,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_STATE_PATH,
    sync_repositories_from_config,
)
from cerebro_python.application.use_cases import RagService


def _load_text(text: str | None, file_path: str | None) -> str:
    if text:
        return text
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    raise ValueError("Use --text or --file")


def _emit(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_cli(
    service: RagService,
    launch_mcp: callable,
    adapter_info: callable,
    symbol_service: object | None = None,
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="cerebro_python")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("mcp", help="Run FastMCP server over stdio")

    p_ingest = sub.add_parser("rag-ingest", help="Ingest document")
    p_ingest.add_argument("--document-id", required=True)
    p_ingest.add_argument("--text")
    p_ingest.add_argument("--file")
    p_ingest.add_argument("--source", default="cli")
    p_ingest.add_argument("--title", default="")
    p_ingest.add_argument("--tags", nargs="*", default=[])
    p_ingest.add_argument("--project-id")
    p_ingest.add_argument("--environment-id")
    p_ingest.add_argument("--session-id")

    p_search = sub.add_parser("rag-search", help="Search documents")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--top-k", type=int, default=5)
    p_search.add_argument("--min-score", type=float)
    p_search.add_argument("--project-id")
    p_search.add_argument("--environment-id")
    p_search.add_argument("--include-environment-id", action="append", default=[])
    p_search.add_argument("--scope-mode", choices=["strict", "custom", "auto"], default="strict")
    p_search.add_argument("--event-time-at")
    p_search.add_argument("--ingested-before")
    p_search.add_argument("--include-inactive", action="store_true")
    p_search.add_argument("--disable-latest-facts", action="store_true")

    p_delete = sub.add_parser("rag-delete", help="Delete document")
    p_delete.add_argument("--document-id", required=True)

    sub.add_parser("rag-stats", help="Show storage stats")
    sub.add_parser("adapters", help="Show selected and available adapters")
    p_symbol_index = sub.add_parser("index-symbol-file", help="Index symbols for a source file")
    p_symbol_index.add_argument("--file", required=True)
    p_symbol_search = sub.add_parser("search-symbols", help="Search indexed symbols")
    p_symbol_search.add_argument("--query", "-q", required=True)
    p_symbol_search.add_argument("--limit", type=int, default=20)
    p_symbol_get = sub.add_parser("get-symbol", help="Retrieve symbol code using byte offsets")
    p_symbol_get.add_argument("--symbol-id", required=True)
    p_symbol_outline = sub.add_parser("get-file-outline", help="Show indexed symbols for a file")
    p_symbol_outline.add_argument("--file", required=True)

    # ── rag-ask: single-shot RAG + MiniMax answer ────────────────────────────
    p_ask = sub.add_parser("rag-ask", help="Ask a question answered with RAG + MiniMax")
    p_ask.add_argument("--question", "-q", required=True, help="Question to ask")
    p_ask.add_argument("--top-k", type=int, default=5, help="Chunks to retrieve (default: 5)")
    p_ask.add_argument("--model", default=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5-highspeed"))
    p_ask.add_argument("--no-sources", action="store_true", help="Hide source chunks")
    p_ask.add_argument("--project-id")
    p_ask.add_argument("--environment-id")

    # ── rag-chat: interactive multi-turn session ─────────────────────────────
    p_chat = sub.add_parser("rag-chat", help="Interactive RAG + MiniMax chat session")
    p_chat.add_argument("--top-k", type=int, default=5)
    p_chat.add_argument("--model", default=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"))

    # ── rag-web-ingest: MiniMax MCP web_search -> auto-ingest into RAG ────────
    p_web_ingest = sub.add_parser("rag-web-ingest",
        help="Search the web with MiniMax MCP and ingest results into RAG")
    p_web_ingest.add_argument("--query", "-q", required=True, help="Web search query")
    p_web_ingest.add_argument("--max-results", type=int, default=5)
    p_web_ingest.add_argument("--document-id", help="Document ID prefix (default: auto)")

    # ── rag-web-ask: web_search + ingest + immediate LLM answer ──────────────
    p_web_ask = sub.add_parser("rag-web-ask",
        help="Web search + ingest + ask MiniMax in one command")
    p_web_ask.add_argument("--query", "-q", required=True, help="Your question")
    p_web_ask.add_argument("--max-results", type=int, default=5)
    p_web_ask.add_argument("--top-k", type=int, default=5)
    p_web_ask.add_argument("--model", default=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"))

    p_sync = sub.add_parser("rag-sync-repos", help="Sync GitHub repositories into local RAG context")
    p_sync.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    p_sync.add_argument("--state", default=str(DEFAULT_STATE_PATH))
    p_sync.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    p_sync.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    p_sync.add_argument("--full-resync", action="store_true")
    p_sync.add_argument("--dry-run", action="store_true")

    p_memory_plan = sub.add_parser(
        "rag-memory-plan",
        help="Recommend CLI/MCP steps to retrieve context or investigate memory/history",
    )
    p_memory_plan.add_argument("--query", "-q", required=True)
    p_memory_plan.add_argument("--top-k", type=int, default=8)
    p_memory_plan.add_argument("--project-id")
    p_memory_plan.add_argument("--environment-id")
    p_memory_plan.add_argument("--include-environment-id", action="append", default=[])

    args = parser.parse_args(argv)

    match args.cmd:
        case "mcp":
            return launch_mcp([])
        case "rag-ingest":
            body = _load_text(args.text, args.file)
            _emit(
                service.ingest(
                    document_id=args.document_id,
                    text=body,
                    metadata={
                        "source": args.source,
                        "title": args.title,
                        "tags": args.tags,
                        "project_id": args.project_id or "",
                        "environment_id": args.environment_id or "",
                        "session_id": args.session_id or "",
                    },
                )
            )
            return 0
        case "rag-search":
            hits = service.search_scoped(
                query=args.query,
                top_k=args.top_k,
                min_score=args.min_score,
                project_id=args.project_id,
                environment_id=args.environment_id,
                include_environment_ids=args.include_environment_id,
                scope_mode=args.scope_mode,
                event_time_at=args.event_time_at,
                ingested_before=args.ingested_before,
                include_inactive=args.include_inactive,
                prefer_latest_facts=not args.disable_latest_facts,
            )
            _emit(
                {
                    "status": "success",
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
            )
            return 0
        case "rag-delete":
            _emit(service.delete(document_id=args.document_id))
            return 0
        case "rag-stats":
            _emit(service.stats())
            return 0
        case "adapters":
            _emit(adapter_info())
            return 0
        case "index-symbol-file":
            if symbol_service is None:
                _emit({"status": "error", "error": "symbol_index_unavailable"})
                return 1
            _emit(
                {
                    "status": "success",
                    "count": len(symbol_service.index_file(args.file)),
                    "file": args.file,
                }
            )
            return 0
        case "search-symbols":
            if symbol_service is None:
                _emit({"status": "error", "error": "symbol_index_unavailable"})
                return 1
            _emit(
                {
                    "status": "success",
                    "count": len(symbol_service.search_symbols(args.query, limit=args.limit)),
                    "results": symbol_service.search_symbols(args.query, limit=args.limit),
                }
            )
            return 0
        case "get-symbol":
            if symbol_service is None:
                _emit({"status": "error", "error": "symbol_index_unavailable"})
                return 1
            _emit(symbol_service.get_symbol(args.symbol_id))
            return 0
        case "get-file-outline":
            if symbol_service is None:
                _emit({"status": "error", "error": "symbol_index_unavailable"})
                return 1
            outline = symbol_service.get_file_outline(args.file)
            _emit({"status": "success", "count": len(outline), "results": outline})
            return 0
        case "rag-ask":
            return _cmd_ask(
                service, args.question, args.top_k, args.model,
                show_sources=not args.no_sources,
                project_id=getattr(args, "project_id", None),
                environment_id=getattr(args, "environment_id", None),
            )
        case "rag-chat":
            return _cmd_chat(service, args.top_k, args.model)
        case "rag-web-ingest":
            return _cmd_web_ingest(service, args.query, args.max_results,
                                   getattr(args, "document_id", None))
        case "rag-web-ask":
            return _cmd_web_ask(service, args.query, args.max_results,
                                args.top_k, args.model)
        case "rag-sync-repos":
            _emit(
                sync_repositories_from_config(
                    service=service,
                    config_path=args.config,
                    state_path=args.state,
                    cache_dir=args.cache_dir,
                    full_resync=args.full_resync,
                    dry_run=args.dry_run,
                    max_file_bytes=args.max_file_bytes,
                )
            )
            return 0
        case "rag-memory-plan":
            _emit(
                build_memory_ops_plan(
                    query=args.query,
                    top_k=args.top_k,
                    project_id=args.project_id,
                    environment_id=args.environment_id,
                    include_environment_ids=args.include_environment_id,
                )
            )
            return 0
        case _:
            return 1


# ─────────────────────────────────────────────────────────────────────────────
# RAG-Ask / RAG-Chat helpers
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Eres Cerebro, un asistente de IA especializado con acceso a una base de conocimientos (RAG).
Responde siempre basandote en el contexto provisto. Si el contexto no cubre la pregunta,
indica que no tienes informacion suficiente en tu memoria pero da tu mejor respuesta.
Responde en el mismo idioma del usuario. Se conciso pero completo.
"""


def _build_minimax_client(model: str):
    """Build an Anthropic client pointed at MiniMax. Returns (client, model) or (None, None)."""
    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        print("ERROR: pip install anthropic requerido.", file=sys.stderr)
        return None, None
    api_key = os.getenv("MINIMAX_API_KEY", "")
    if not api_key:
        print("ERROR: MINIMAX_API_KEY no configurado en .env", file=sys.stderr)
        return None, None
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url="https://api.minimax.io/anthropic",
    )
    return client, model


def _rag_context(
    service: RagService,
    question: str,
    top_k: int,
    project_id: str | None = None,
    environment_id: str | None = None,
) -> tuple[str, list]:
    """Retrieve top-K chunks and format them as a numbered context block."""
    hits = service.search_scoped(
        query=question,
        top_k=top_k,
        project_id=project_id,
        environment_id=environment_id,
    )
    if not hits:
        return "Sin contexto relevante en memoria.", []
    parts = [f"[{i}] (score={h.score:.3f}) {h.chunk_text.strip()}" for i, h in enumerate(hits, 1)]
    return "\n\n".join(parts), hits


def _call_minimax(client, model: str, system: str, messages: list[dict]) -> str:
    """Call MiniMax via Anthropic SDK and return the first text block."""
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=messages,
    )
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            return block.text
    return ""


def _cmd_ask(
    service: RagService,
    question: str,
    top_k: int,
    model: str,
    show_sources: bool = True,
    project_id: str | None = None,
    environment_id: str | None = None,
) -> int:
    """Single-shot RAG + MiniMax answer."""
    client, model = _build_minimax_client(model)
    if client is None:
        return 1

    context, hits = _rag_context(service, question, top_k, project_id, environment_id)
    prompt = f"Contexto recuperado de la memoria:\n\n{context}\n\nPregunta: {question}"

    print(f"\nConsultando MiniMax ({model}) con {len(hits)} fragmentos...\n")
    reply = _call_minimax(client, model, SYSTEM_PROMPT, [{"role": "user", "content": prompt}])
    print(reply)

    if show_sources and hits:
        print("\n-- Fuentes " + "-" * 30)
        for i, h in enumerate(hits, 1):
            doc = h.metadata.get("title") or h.document_id
            print(f"  [{i}] {doc}  (score={h.score:.3f})")
    return 0


def _cmd_chat(service: RagService, top_k: int, model: str) -> int:
    """Interactive multi-turn RAG + MiniMax chat loop."""
    client, model = _build_minimax_client(model)
    if client is None:
        return 1

    history: list[dict] = []
    stats = service.stats()
    total_docs = stats.get("documents", "?")
    print(f"Cerebro Chat  |  modelo: {model}  |  documentos en memoria: {total_docs}")
    print("Comandos: /limpiar  /salir\n")

    while True:
        try:
            user_input = input("Tu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego!")
            return 0

        if not user_input:
            continue
        if user_input.lower() in ("/salir", "/exit", "exit", "quit"):
            print("Hasta luego!")
            return 0
        if user_input.lower() in ("/limpiar", "/clear"):
            history.clear()
            print("[Historial limpiado]\n")
            continue

        context, hits = _rag_context(service, user_input, top_k)
        rag_msg = f"Contexto relevante:\n{context}\n\nPregunta: {user_input}"
        history.append({"role": "user", "content": rag_msg})

        reply = _call_minimax(client, model, SYSTEM_PROMPT, history)
        history.append({"role": "assistant", "content": reply})

        print(f"\nCerebro: {reply}\n")
        if hits:
            sources = ", ".join((h.metadata.get("title") or h.document_id) for h in hits[:3])
            print(f"   [{len(hits)} fragmentos: {sources}...]\n")
def _cmd_web_ingest(
    service: RagService,
    query: str,
    max_results: int = 5,
    document_id_prefix: str | None = None,
) -> int:
    """Search the web with MiniMax MCP and ingest results into the RAG."""
    from cerebro_python.adapters.llm.minimax_mcp_client import MinimaxMCPClient  # noqa: PLC0415

    client = MinimaxMCPClient()
    if not client.is_available:
        print("ERROR: MINIMAX_API_KEY not set", file=sys.stderr)
        return 1

    print(f"Buscando en la web: '{query}'...")
    results = client.web_search(query)
    if not results:
        print("Sin resultados de busqueda.")
        return 0

    safe_query = "".join(ch if ch.isalnum() else "-" for ch in query)[:40].strip("-")
    ingested = 0
    for i, r in enumerate(results[:max_results], 1):
        title = r.get("title", f"result-{i}")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        if not snippet:
            continue

        doc_id = f"{document_id_prefix or 'web'}-{safe_query}-{i}"
        text = f"Titulo: {title}\nFuente: {url}\n\n{snippet}"
        result = service.ingest(
            document_id=doc_id,
            text=text,
            metadata={"source": "web_search", "title": title, "url": url,
                      "query": query, "tags": ["web", "minimax-mcp"]},
        )
        status = result.get("status", "?")
        chunks = result.get("chunks", 0)
        print(f"  [{i}] {title[:60]} -> {doc_id} ({chunks} chunks, {status})")
        ingested += 1

    print(f"\nIngested {ingested}/{len(results[:max_results])} resultados. Listos para rag-ask.")
    return 0


def _cmd_web_ask(
    service: RagService,
    query: str,
    max_results: int = 5,
    top_k: int = 5,
    model: str = "MiniMax-M2.5",
) -> int:
    """Web search + ingest + RAG answer in a single command."""
    # 1. Ingest fresh web context
    print(f"[1/3] Buscando y cargando contexto web para: '{query}'")
    rc = _cmd_web_ingest(service, query, max_results)
    if rc != 0:
        return rc

    # 2. Answer with RAG + LLM
    print(f"\n[2/3] Consultando RAG + MiniMax ({model})...")
    return _cmd_ask(service, query, top_k, model, show_sources=True)
