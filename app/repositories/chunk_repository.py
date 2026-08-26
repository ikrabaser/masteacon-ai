"""Data-access layer for the DocumentChunk model, including pgvector similarity search."""
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.reciprocal_rank_fusion import reciprocal_rank_fusion_scores


class ChunkRepository:
    """Encapsulates all database queries related to DocumentChunk rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete_by_document_id(self, document_id: int) -> None:
        """Remove any existing chunks for a document before re-indexing it."""
        await self._session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        await self._session.flush()

    async def bulk_create(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        self._session.add_all(chunks)
        await self._session.flush()
        return chunks

    async def list_content_by_document_id(self, document_id: int) -> list[str]:
        """Return chunk contents for a document, in original chunk order."""
        result = await self._session.execute(
            select(DocumentChunk.content)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def count_by_document_id(self, document_id: int) -> int:
        """Count chunks without touching the Document.chunks lazy relationship.

        Avoids triggering an implicit, unawaited lazy load on an async session
        (which raises MissingGreenlet) when callers only need the count.
        """
        result = await self._session.execute(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return result.scalar_one()

    async def similarity_search(
        self,
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
        workspace_id: int,
        document_id: int | None = None,
        content_type: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Return (chunk, similarity_score) pairs ordered by cosine similarity, most similar first.

        `workspace_id` is mandatory (not optional) so no call site can accidentally
        run an unscoped search: a chunk belonging to another workspace must never be
        returned, even if its similarity score would otherwise rank higher.
        `document_id` and `content_type`, if given, further narrow the search.

        pgvector's `cosine_distance` returns a value in [0, 2] where 0 means identical.
        We convert it to a similarity score in [-1, 1] (1 == identical) for the API response.
        """
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(DocumentChunk, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .options(joinedload(DocumentChunk.document))
            .where(DocumentChunk.embedding.isnot(None), Document.workspace_id == workspace_id)
            .order_by(distance)
            .limit(limit)
        )
        if document_id is not None:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if content_type is not None:
            stmt = stmt.where(Document.content_type == content_type)
        result = await self._session.execute(stmt)
        rows = result.all()

        matches: list[tuple[DocumentChunk, float]] = []
        for chunk, dist in rows:
            similarity = 1 - dist
            if similarity >= similarity_threshold:
                matches.append((chunk, similarity))
        return matches

    async def keyword_search(
        self,
        query_text: str,
        limit: int,
        workspace_id: int,
        document_id: int | None = None,
        content_type: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Full-text (keyword/BM25-style) search over chunk content via PostgreSQL's
        built-in text search — catches exact technical terms (error codes, config
        keys, class names) that a pure embedding match can sometimes miss, e.g. a
        query for "ERR_CONNECTION_REFUSED" against a chunk that contains it verbatim.

        Uses the GIN index on `to_tsvector('english', content)` (see migration 0007)
        via the same expression, so this is index-backed, not a sequential scan.
        Same mandatory `workspace_id` / optional `document_id` / `content_type`
        scoping contract as `similarity_search`.
        """
        query_text = query_text.strip()
        if not query_text:
            return []

        ts_vector = func.to_tsvector("english", DocumentChunk.content)
        ts_query = func.plainto_tsquery("english", query_text)
        rank = func.ts_rank(ts_vector, ts_query)

        stmt = (
            select(DocumentChunk, rank.label("rank"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .options(joinedload(DocumentChunk.document))
            .where(ts_vector.op("@@")(ts_query), Document.workspace_id == workspace_id)
            .order_by(rank.desc())
            .limit(limit)
        )
        if document_id is not None:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if content_type is not None:
            stmt = stmt.where(Document.content_type == content_type)

        result = await self._session.execute(stmt)
        return [(chunk, float(rank_value)) for chunk, rank_value in result.all()]

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
        workspace_id: int,
        document_id: int | None = None,
        content_type: str | None = None,
        candidate_count: int | None = None,
        rrf_k: int = 60,
    ) -> list[tuple[DocumentChunk, float]]:
        """Combine vector similarity search and keyword (full-text) search via
        Reciprocal Rank Fusion (RRF), instead of relying on embeddings alone.

        Each side independently ranks up to `candidate_count` (or `limit`, if not
        given) chunks; a chunk's fused score is the sum of `1 / (rrf_k + rank)`
        across whichever list(s) it appears in (rank is 1-based), so a chunk that
        ranks highly on *either* side — semantic similarity or an exact keyword
        match — surfaces near the top, and one that ranks well on *both* sides
        rises above either alone. `rrf_k=60` is the standard default from the
        original RRF paper; it just controls how quickly a rank's contribution
        decays, and the fusion is not sensitive to small changes in it.

        The returned score is the chunk's *vector* similarity when it was found by
        the vector side (0.0 for a chunk that only matched by keyword), so the
        existing "cosine similarity" meaning of this score is preserved for
        callers/API responses — RRF is used purely to decide ranking/order, not
        to replace the displayed score.
        """
        fetch_limit = candidate_count or limit

        vector_matches = await self.similarity_search(
            query_embedding=query_embedding,
            limit=fetch_limit,
            similarity_threshold=similarity_threshold,
            workspace_id=workspace_id,
            document_id=document_id,
            content_type=content_type,
        )
        keyword_matches = await self.keyword_search(
            query_text=query_text,
            limit=fetch_limit,
            workspace_id=workspace_id,
            document_id=document_id,
            content_type=content_type,
        )

        fused_scores = reciprocal_rank_fusion_scores(
            [
                [chunk.id for chunk, _ in vector_matches],
                [chunk.id for chunk, _ in keyword_matches],
            ],
            rrf_k=rrf_k,
        )

        chunks_by_id: dict[int, DocumentChunk] = {chunk.id: chunk for chunk, _ in vector_matches}
        similarity_by_id: dict[int, float] = {chunk.id: similarity for chunk, similarity in vector_matches}
        for chunk, _keyword_rank in keyword_matches:
            chunks_by_id.setdefault(chunk.id, chunk)
            similarity_by_id.setdefault(chunk.id, 0.0)

        ordered_ids = sorted(fused_scores, key=lambda chunk_id: fused_scores[chunk_id], reverse=True)[:limit]
        return [(chunks_by_id[chunk_id], similarity_by_id[chunk_id]) for chunk_id in ordered_ids]

    async def commit(self) -> None:
        await self._session.commit()
