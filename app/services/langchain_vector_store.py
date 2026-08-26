"""A LangChain `VectorStore` adapter over our existing pgvector-backed `ChunkRepository`.

Documents are indexed through the async Celery pipeline (`DocumentIndexingService`
-> `ChunkRepository.bulk_create`), never through this adapter's `add_texts`/
`from_texts` — this class exists purely to expose our already-indexed,
workspace-scoped chunks through LangChain's standard `VectorStore` interface, so
retrieval is composed using LangChain's own `Document`/`VectorStore` primitives
instead of ad hoc tuples.

Workspace isolation is preserved exactly as before: `workspace_id` is a
mandatory, non-bypassable filter key (never optional), and every query is still
executed by `ChunkRepository.similarity_search`, which scopes the SQL itself.
"""
from typing import Any, Iterable

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from app.repositories.chunk_repository import ChunkRepository
from app.services.embedding_service import EmbeddingService


class MissingWorkspaceFilterError(ValueError):
    """Raised when a search is attempted without the mandatory workspace_id filter."""


class EmbeddingServiceAdapter(Embeddings):
    """Adapts our async `EmbeddingService` (and its pluggable EmbeddingProvider,
    fake or real) to LangChain's `Embeddings` interface, so it can back a
    LangChain `VectorStore`.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("This adapter is async-only; use `aembed_documents`.")

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("This adapter is async-only; use `aembed_query`.")

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embedding_service.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await self._embedding_service.embed_query(text)


class ChunkVectorStore(VectorStore):
    """Exposes indexed `DocumentChunk` rows as a LangChain `VectorStore`."""

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        embeddings: Embeddings,
        similarity_threshold: float,
        hybrid_search_enabled: bool = False,
        hybrid_candidate_count: int | None = None,
    ) -> None:
        self._chunks = chunk_repository
        self._embeddings = embeddings
        self._similarity_threshold = similarity_threshold
        # Hybrid search: fuse vector similarity with PostgreSQL full-text
        # (keyword) search via Reciprocal Rank Fusion, so an exact technical
        # term a pure embedding match might miss still surfaces. Disabled by
        # default — off means byte-for-byte the same behavior as before.
        self._hybrid_search_enabled = hybrid_search_enabled
        self._hybrid_candidate_count = hybrid_candidate_count

    @property
    def embeddings(self) -> Embeddings:
        return self._embeddings

    async def asimilarity_search_with_score(
        self, query: str, k: int = 4, filter: dict[str, Any] | None = None, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        filter = filter or {}
        workspace_id = filter.get("workspace_id")
        if workspace_id is None:
            raise MissingWorkspaceFilterError(
                "similarity_search on ChunkVectorStore requires a 'workspace_id' filter — "
                "unscoped searches across workspaces are never allowed."
            )

        query_embedding = await self._embeddings.aembed_query(query)
        if self._hybrid_search_enabled:
            matches = await self._chunks.hybrid_search(
                query_text=query,
                query_embedding=query_embedding,
                limit=k,
                similarity_threshold=self._similarity_threshold,
                workspace_id=workspace_id,
                document_id=filter.get("document_id"),
                content_type=filter.get("content_type"),
                candidate_count=self._hybrid_candidate_count,
            )
        else:
            matches = await self._chunks.similarity_search(
                query_embedding=query_embedding,
                limit=k,
                similarity_threshold=self._similarity_threshold,
                workspace_id=workspace_id,
                document_id=filter.get("document_id"),
                content_type=filter.get("content_type"),
            )
        return [
            (
                Document(
                    page_content=chunk.content,
                    metadata={
                        "document_id": chunk.document_id,
                        "filename": chunk.document.filename,
                        "chunk_index": chunk.chunk_index,
                    },
                ),
                score,
            )
            for chunk, score in matches
        ]

    async def asimilarity_search(
        self, query: str, k: int = 4, filter: dict[str, Any] | None = None, **kwargs: Any
    ) -> list[Document]:
        results = await self.asimilarity_search_with_score(query, k=k, filter=filter, **kwargs)
        return [doc for doc, _ in results]

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Document]:
        # This adapter is async-only, matching the rest of the FastAPI/SQLAlchemy-async
        # stack it sits on top of — the application never calls the sync path.
        raise NotImplementedError("ChunkVectorStore is async-only; use `asimilarity_search*`.")

    def add_texts(self, texts: Iterable[str], metadatas: list[dict] | None = None, **kwargs: Any) -> list[str]:
        raise NotImplementedError(
            "Indexing happens through the async document-indexing pipeline "
            "(DocumentIndexingService -> ChunkRepository.bulk_create), not through this adapter."
        )

    @classmethod
    def from_texts(
        cls, texts: list[str], embedding: Embeddings, metadatas: list[dict] | None = None, **kwargs: Any
    ) -> "ChunkVectorStore":
        raise NotImplementedError(
            "ChunkVectorStore wraps already-indexed chunks; construct it directly with a "
            "ChunkRepository instead of via from_texts()."
        )
