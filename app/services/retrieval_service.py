"""Semantic retrieval service: embeds a query and finds the most similar chunks.

Question -> Query Rewriter -> Embedding -> Vector Search -> Top N Candidates ->
Reranker -> Top K -> RAG. Vector search itself is done through
`ChunkVectorStore`, a LangChain `VectorStore` adapter over our pgvector-backed
`ChunkRepository` (see langchain_vector_store.py), so retrieval is expressed in
LangChain's own `Document`/`VectorStore` terms. Query rewriting and reranking
are both optional: when neither is wired in (or disabled via config), this
behaves exactly like plain vector search, fetching and returning
`default_top_k` (or the caller-provided `limit`) results directly. Which
QueryRewriter/Reranker implementation is used is decided by the caller (see
app.api.dependencies) — this service only depends on their shared interfaces.
"""
from app.repositories.chunk_repository import ChunkRepository
from app.services.embedding_service import EmbeddingService
from app.services.langchain_vector_store import ChunkVectorStore, EmbeddingServiceAdapter
from app.services.retrieval_types import QueryRewriter, Reranker, RetrievedChunk

__all__ = ["RetrievedChunk", "RetrievalService"]


class RetrievalService:
    """Performs semantic (vector) search over indexed document chunks, with optional reranking."""

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        embedding_service: EmbeddingService,
        default_top_k: int,
        similarity_threshold: float,
        reranking_service: Reranker | None = None,
        candidate_count: int | None = None,
        rerank_top_k: int | None = None,
        hybrid_search_enabled: bool = False,
        query_rewriting_service: QueryRewriter | None = None,
    ) -> None:
        self._query_rewriting_service = query_rewriting_service
        self._vector_store = ChunkVectorStore(
            chunk_repository=chunk_repository,
            embeddings=EmbeddingServiceAdapter(embedding_service),
            similarity_threshold=similarity_threshold,
            hybrid_search_enabled=hybrid_search_enabled,
            hybrid_candidate_count=candidate_count,
        )
        self._default_top_k = default_top_k
        self._reranking_service = reranking_service
        # Only meaningful when reranking is enabled — how many candidates to pull
        # from vector search before the reranker narrows them down to top_k.
        self._candidate_count = candidate_count or default_top_k
        # The default final count *after* reranking, when the caller doesn't
        # explicitly request a different `limit`.
        self._rerank_top_k = rerank_top_k or default_top_k

    async def search(
        self,
        query: str,
        workspace_id: int,
        limit: int | None = None,
        document_id: int | None = None,
        content_type: str | None = None,
    ) -> list[RetrievedChunk]:
        query = query.strip()
        if not query:
            return []

        if limit is not None:
            top_k = limit
        elif self._reranking_service is not None:
            top_k = self._rerank_top_k
        else:
            top_k = self._default_top_k
        fetch_limit = max(self._candidate_count, top_k) if self._reranking_service else top_k

        search_filter: dict[str, int | str] = {"workspace_id": workspace_id}
        if document_id is not None:
            search_filter["document_id"] = document_id
        if content_type is not None:
            search_filter["content_type"] = content_type

        # Rewriting only changes what's embedded/keyword-searched to find
        # candidates — reranking below still judges relevance against the
        # user's actual original question, not the expanded retrieval query.
        retrieval_query = query
        if self._query_rewriting_service is not None:
            retrieval_query = await self._query_rewriting_service.rewrite(query)

        matches = await self._vector_store.asimilarity_search_with_score(
            retrieval_query, k=fetch_limit, filter=search_filter
        )

        candidates = [
            RetrievedChunk(
                document_id=doc.metadata["document_id"],
                filename=doc.metadata["filename"],
                chunk_index=doc.metadata["chunk_index"],
                content=doc.page_content,
                similarity_score=round(score, 4),
            )
            for doc, score in matches
        ]

        if self._reranking_service is None:
            return candidates[:top_k]
        return self._reranking_service.rerank(query, candidates, top_k)
