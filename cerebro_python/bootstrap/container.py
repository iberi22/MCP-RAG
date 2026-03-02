"""Bootstrap wiring for hexagonal architecture."""

from __future__ import annotations

import os

from cerebro_python.adapters.chunking.simple_chunker import SimpleChunker
from cerebro_python.adapters.chunking.ast_chunker import AstChunker
from cerebro_python.adapters.embeddings.hash_embedding import HashEmbeddingAdapter
from cerebro_python.adapters.embeddings.ollama_embedding import OllamaEmbeddingAdapter
from cerebro_python.adapters.mcp.server import build_mcp
from cerebro_python.adapters.policies.identity_policy import IdentityMemoryPolicy
from cerebro_python.adapters.policies.smart_memory_policy import SmartMemoryPolicy
from cerebro_python.adapters.query_rewrite.identity_rewriter import IdentityQueryRewriter
from cerebro_python.adapters.query_rewrite.rules_rewriter import RulesQueryRewriter
from cerebro_python.adapters.ranking.hybrid_ranker import HybridRankerAdapter
from cerebro_python.adapters.reranking.heuristic_reranker import HeuristicRerankerAdapter
from cerebro_python.adapters.reranking.identity_reranker import IdentityRerankerAdapter
from cerebro_python.adapters.scope.auto_scope_strategy import AutoScopeStrategy
from cerebro_python.adapters.scope.strict_scope_strategy import StrictScopeStrategy
from cerebro_python.adapters.storage.inmemory_repository import InMemoryRepository
from cerebro_python.adapters.storage.sqlite_repository import SqliteMemoryRepository
from cerebro_python.application.adapter_registry import AdapterRegistry
from cerebro_python.application.use_cases import RagService


class Container:
    def __init__(self):
        self.registry = AdapterRegistry()
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        db_path = os.getenv("RAG_DB_PATH", "cerebro_rag.db")
        self.registry.register("repository", "sqlite", lambda: SqliteMemoryRepository(db_path=db_path))
        self.registry.register("repository", "memory", InMemoryRepository)

        chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "900"))
        chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
        self.registry.register("chunker", "simple", lambda: SimpleChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap))
        self.registry.register("chunker", "ast", AstChunker)

        self.registry.register("embedder", "hash", lambda: HashEmbeddingAdapter(dims=int(os.getenv("RAG_HASH_DIMS", "256"))))
        self.registry.register(
            "embedder",
            "ollama",
            lambda: OllamaEmbeddingAdapter(
                base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                model=os.getenv("OLLAMA_MODEL", "nomic-embed-text"),
                timeout=float(os.getenv("OLLAMA_TIMEOUT", "20")),
                fallback=HashEmbeddingAdapter(dims=int(os.getenv("RAG_HASH_DIMS", "256"))),
            ),
        )
        self.registry.register(
            "ranker",
            "hybrid",
            lambda: HybridRankerAdapter(
                semantic_weight=float(os.getenv("RAG_SEMANTIC_WEIGHT", "0.75")),
                lexical_weight=float(os.getenv("RAG_LEXICAL_WEIGHT", "0.25")),
                rrf_k=int(os.getenv("RAG_RRF_K", "50")),
                mmr_lambda=float(os.getenv("RAG_MMR_LAMBDA", "0.75")),
            ),
        )
        self.registry.register("policy", "identity", IdentityMemoryPolicy)
        self.registry.register(
            "policy",
            "smart",
            lambda: SmartMemoryPolicy(
                min_chunk_chars=int(os.getenv("RAG_MIN_CHUNK_CHARS", "24")),
                max_chunks_per_document=int(os.getenv("RAG_MAX_CHUNKS_PER_DOC", "128")),
            ),
        )
        self.registry.register("reranker", "identity", IdentityRerankerAdapter)
        self.registry.register(
            "reranker",
            "heuristic",
            lambda: HeuristicRerankerAdapter(
                base_weight=float(os.getenv("RAG_RERANK_BASE_WEIGHT", "0.7")),
                lexical_weight=float(os.getenv("RAG_RERANK_LEXICAL_WEIGHT", "0.3")),
                phrase_boost=float(os.getenv("RAG_RERANK_PHRASE_BOOST", "0.1")),
            ),
        )
        self.registry.register("query_rewriter", "identity", IdentityQueryRewriter)
        self.registry.register("query_rewriter", "rules", RulesQueryRewriter)
        self.registry.register("scope_strategy", "strict", StrictScopeStrategy)
        self.registry.register("scope_strategy", "auto", AutoScopeStrategy)

    def build_service(self) -> RagService:
        selected = self.selected_adapters()
        repo_name = selected["repository"]
        chunker_name = selected["chunker"]
        embedder_name = selected["embedder"]
        ranker_name = selected["ranker"]
        policy_name = selected["policy"]
        reranker_name = selected["reranker"]
        query_rewriter_name = selected["query_rewriter"]
        scope_strategy_name = selected["scope_strategy"]

        repository = self.registry.create("repository", repo_name)
        chunker = self.registry.create("chunker", chunker_name)
        embedder = self.registry.create("embedder", embedder_name)
        ranker = self.registry.create("ranker", ranker_name)
        policy = self.registry.create("policy", policy_name)
        reranker = self.registry.create("reranker", reranker_name)
        query_rewriter = self.registry.create("query_rewriter", query_rewriter_name)
        scope_strategy = self.registry.create("scope_strategy", scope_strategy_name)
        return RagService(
            repository=repository,
            chunker=chunker,
            embedder=embedder,
            ranker=ranker,
            memory_policy=policy,
            reranker=reranker,
            query_rewriter=query_rewriter,
            scope_strategy=scope_strategy,
            retrieval_multiplier=int(os.getenv("RAG_RETRIEVAL_MULTIPLIER", "4")),
            min_score=float(os.getenv("RAG_MIN_SCORE", "-1.0")),
        )

    def build_mcp(self):
        return build_mcp(self.build_service())

    def selected_adapters(self) -> dict[str, str]:
        return {
            "repository": os.getenv("RAG_REPOSITORY_ADAPTER", "sqlite"),
            "chunker": os.getenv("RAG_CHUNKER_ADAPTER", "simple"),
            "embedder": os.getenv("RAG_EMBEDDING_ADAPTER", os.getenv("RAG_EMBED_PROVIDER", "hash")),
            "ranker": os.getenv("RAG_RANKER_ADAPTER", "hybrid"),
            "policy": os.getenv("RAG_MEMORY_POLICY_ADAPTER", "smart"),
            "reranker": os.getenv("RAG_RERANKER_ADAPTER", "heuristic"),
            "query_rewriter": os.getenv("RAG_QUERY_REWRITER_ADAPTER", "rules"),
            "scope_strategy": os.getenv("RAG_SCOPE_STRATEGY_ADAPTER", "strict"),
        }

    def available_adapters(self) -> dict[str, list[str]]:
        return {
            "repository": self.registry.options("repository"),
            "chunker": self.registry.options("chunker"),
            "embedder": self.registry.options("embedder"),
            "ranker": self.registry.options("ranker"),
            "policy": self.registry.options("policy"),
            "reranker": self.registry.options("reranker"),
            "query_rewriter": self.registry.options("query_rewriter"),
            "scope_strategy": self.registry.options("scope_strategy"),
        }
