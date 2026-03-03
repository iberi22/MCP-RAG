"""Multi-level RAG evaluation for scoped retrieval quality."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cerebro_python.adapters.chunking.simple_chunker import SimpleChunker
from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter
from cerebro_python.adapters.policies.smart_memory_policy import SmartMemoryPolicy
from cerebro_python.adapters.query_rewrite.rules_rewriter import RulesQueryRewriter
from cerebro_python.adapters.ranking.hybrid_ranker import HybridRankerAdapter
from cerebro_python.adapters.reranking.heuristic_reranker import HeuristicRerankerAdapter
from cerebro_python.adapters.scope.auto_scope_strategy import AutoScopeStrategy
from cerebro_python.adapters.storage.inmemory_repository import InMemoryRepository
from cerebro_python.application.use_cases import RagService


@dataclass(slots=True)
class LevelResult:
    level: str
    passed: bool
    details: dict[str, object]
    latency_ms: float


def build_service() -> RagService:
    return RagService(
        repository=InMemoryRepository(),
        chunker=SimpleChunker(chunk_size=260, chunk_overlap=30),
        embedder=HashEmbeddingAdapter(dims=256),
        ranker=HybridRankerAdapter(),
        memory_policy=SmartMemoryPolicy(min_chunk_chars=20, max_chunks_per_document=128),
        reranker=HeuristicRerankerAdapter(),
        query_rewriter=RulesQueryRewriter(),
        scope_strategy=AutoScopeStrategy(),
        retrieval_multiplier=5,
        min_score=-1.0,
    )


def seed(service: RagService) -> None:
    docs = [
        ("alpha-dev-api", "alpha api architecture uses modular routers and adapters", "alpha", "dev"),
        ("alpha-dev-tests", "alpha project enforces unit tests for adapters and use cases", "alpha", "dev"),
        ("alpha-prod-runbook", "alpha production runbook includes rollback strategy and release checklist", "alpha", "prod"),
        ("beta-dev-guides", "beta coding guide emphasizes clean boundaries and repository abstractions", "beta", "dev"),
        ("beta-prod-ops", "beta production operations and deployment approvals", "beta", "prod"),
    ]
    for doc_id, text, project_id, env_id in docs:
        service.ingest(
            document_id=doc_id,
            text=text,
            metadata={"project_id": project_id, "environment_id": env_id, "source": "eval"},
        )


def level_1_smoke(service: RagService) -> LevelResult:
    t0 = time.perf_counter()
    hits = service.search_scoped(query="modular routers adapters", top_k=3, project_id="alpha", environment_id="dev")
    return LevelResult(
        level="level_1_smoke",
        passed=bool(hits),
        details={"hit_count": len(hits), "top_document": hits[0].document_id if hits else ""},
        latency_ms=(time.perf_counter() - t0) * 1000,
    )


def level_2_isolation(service: RagService) -> LevelResult:
    t0 = time.perf_counter()
    hits = service.search_scoped(
        query="deployment approvals",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        scope_mode="strict",
    )
    leaked = [h.document_id for h in hits if h.metadata.get("project_id") != "alpha" or h.metadata.get("environment_id") != "dev"]
    return LevelResult(
        level="level_2_isolation",
        passed=not leaked,
        details={"hit_count": len(hits), "leaked_documents": leaked},
        latency_ms=(time.perf_counter() - t0) * 1000,
    )


def level_3_cross_environment(service: RagService) -> LevelResult:
    t0 = time.perf_counter()
    hits = service.search_scoped(
        query="rollback release checklist",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        include_environment_ids=["prod"],
        scope_mode="custom",
    )
    contains_prod = any(h.metadata.get("environment_id") == "prod" for h in hits)
    only_alpha = all(h.metadata.get("project_id") == "alpha" for h in hits)
    return LevelResult(
        level="level_3_cross_environment",
        passed=contains_prod and only_alpha,
        details={"hit_count": len(hits), "contains_prod": contains_prod, "only_alpha": only_alpha},
        latency_ms=(time.perf_counter() - t0) * 1000,
    )


def level_4_temporal(service: RagService) -> LevelResult:
    t0 = time.perf_counter()
    service.ingest(
        document_id="alpha-policy-v1",
        text="alpha policy old version",
        metadata={"project_id": "alpha", "environment_id": "dev", "fact_key": "policy", "event_time": "2025-01-01T00:00:00+00:00"},
    )
    service.ingest(
        document_id="alpha-policy-v2",
        text="alpha policy new version",
        metadata={"project_id": "alpha", "environment_id": "dev", "fact_key": "policy", "event_time": "2026-01-01T00:00:00+00:00"},
    )
    hits = service.search_scoped(
        query="alpha policy",
        top_k=5,
        project_id="alpha",
        environment_id="dev",
        event_time_at="2025-12-31T00:00:00+00:00",
    )
    docs = {h.document_id for h in hits}
    return LevelResult(
        level="level_4_temporal",
        passed=("alpha-policy-v1" in docs and "alpha-policy-v2" not in docs),
        details={"documents": sorted(docs)},
        latency_ms=(time.perf_counter() - t0) * 1000,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--levels", nargs="*", default=["all"])
    args = parser.parse_args()

    levels = {
        "level_1_smoke": level_1_smoke,
        "level_2_isolation": level_2_isolation,
        "level_3_cross_environment": level_3_cross_environment,
        "level_4_temporal": level_4_temporal,
    }
    selected = list(levels) if "all" in args.levels else [x for x in args.levels if x in levels]
    if not selected:
        print(json.dumps({"status": "error", "error": "no_valid_levels"}, indent=2))
        return 2

    service = build_service()
    seed(service)
    results = [levels[name](service) for name in selected]
    passed = all(r.passed for r in results)
    print(
        json.dumps(
            {
                "status": "success" if passed else "failed",
                "passed": passed,
                "summary": {"passed_count": sum(1 for r in results if r.passed), "total": len(results)},
                "results": [asdict(r) for r in results],
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
