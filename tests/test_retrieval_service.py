"""Tests for RetrievalService using fake repository/embedding provider."""
import pytest

from app.services.embedding_service import EmbeddingService
from app.services.reranking_service import RerankingService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeChunkRepository, FakeChunkRow, FakeEmbeddingProvider

WORKSPACE_ID = 1


@pytest.mark.asyncio
async def test_search_returns_results_above_threshold() -> None:
    rows = [
        FakeChunkRow(1, "handbook.pdf", 0, "Annual leave policy is 14 days.", 0.91, workspace_id=WORKSPACE_ID),
        FakeChunkRow(1, "handbook.pdf", 1, "Sick leave policy is 10 days.", 0.40, workspace_id=WORKSPACE_ID),
        FakeChunkRow(2, "other.pdf", 0, "Unrelated content.", 0.10, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.3,
    )

    results = await retrieval_service.search("annual leave policy", workspace_id=WORKSPACE_ID)

    assert len(results) == 2
    assert results[0].similarity_score >= results[1].similarity_score


@pytest.mark.asyncio
async def test_search_returns_empty_list_for_blank_query() -> None:
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository([]),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.3,
    )

    results = await retrieval_service.search("   ", workspace_id=WORKSPACE_ID)

    assert results == []


@pytest.mark.asyncio
async def test_search_respects_limit() -> None:
    rows = [
        FakeChunkRow(1, "doc.pdf", i, f"chunk {i}", 0.9 - i * 0.01, workspace_id=WORKSPACE_ID)
        for i in range(10)
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )

    results = await retrieval_service.search("query", workspace_id=WORKSPACE_ID, limit=3)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_search_never_returns_chunks_from_another_workspace() -> None:
    """Even a much higher similarity score in another workspace must never leak through."""
    rows = [
        FakeChunkRow(1, "mine.pdf", 0, "My own content.", 0.20, workspace_id=WORKSPACE_ID),
        FakeChunkRow(2, "someone-elses.pdf", 0, "Someone else's content.", 0.99, workspace_id=999),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )

    results = await retrieval_service.search("anything", workspace_id=WORKSPACE_ID)

    assert len(results) == 1
    assert results[0].filename == "mine.pdf"


@pytest.mark.asyncio
async def test_search_can_be_scoped_to_a_single_document() -> None:
    rows = [
        FakeChunkRow(1, "a.pdf", 0, "Content A.", 0.80, workspace_id=WORKSPACE_ID),
        FakeChunkRow(2, "b.pdf", 0, "Content B.", 0.90, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )

    results = await retrieval_service.search("anything", workspace_id=WORKSPACE_ID, document_id=1)

    assert len(results) == 1
    assert results[0].filename == "a.pdf"


@pytest.mark.asyncio
async def test_search_can_be_scoped_to_a_content_type() -> None:
    rows = [
        FakeChunkRow(1, "a.pdf", 0, "Content A.", 0.80, workspace_id=WORKSPACE_ID, content_type="application/pdf"),
        FakeChunkRow(2, "b.txt", 0, "Content B.", 0.90, workspace_id=WORKSPACE_ID, content_type="text/plain"),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )

    results = await retrieval_service.search("anything", workspace_id=WORKSPACE_ID, content_type="application/pdf")

    assert len(results) == 1
    assert results[0].filename == "a.pdf"


@pytest.mark.asyncio
async def test_search_without_reranking_service_is_unaffected_by_rerank_settings() -> None:
    """No RerankingService wired in => identical behavior to before reranking existed."""
    rows = [FakeChunkRow(i, f"doc-{i}.pdf", 0, f"chunk {i}", 0.9 - i * 0.01, workspace_id=WORKSPACE_ID) for i in range(10)]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
        reranking_service=None,
        candidate_count=20,
        rerank_top_k=2,
    )

    results = await retrieval_service.search("query", workspace_id=WORKSPACE_ID)

    # rerank_top_k is ignored entirely when there's no reranker — default_top_k wins.
    assert len(results) == 5


@pytest.mark.asyncio
async def test_search_with_reranking_fetches_candidates_then_truncates_to_rerank_top_k() -> None:
    rows = [
        FakeChunkRow(1, "off-topic.pdf", 0, "Completely unrelated filler content.", 0.95, workspace_id=WORKSPACE_ID),
        FakeChunkRow(
            2, "on-topic.pdf", 0, "Annual leave policy grants fourteen days per year.", 0.40, workspace_id=WORKSPACE_ID
        ),
        *[
            FakeChunkRow(10 + i, f"filler-{i}.pdf", 0, "irrelevant filler", 0.3, workspace_id=WORKSPACE_ID)
            for i in range(5)
        ],
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
        reranking_service=RerankingService(lexical_weight=0.9),
        candidate_count=20,
        rerank_top_k=2,
    )

    results = await retrieval_service.search("annual leave policy", workspace_id=WORKSPACE_ID)

    # Reranked to just 2 results, and the lexically-matching chunk wins first place
    # despite its lower raw vector similarity score.
    assert len(results) == 2
    assert results[0].document_id == 2


@pytest.mark.asyncio
async def test_hybrid_search_disabled_is_unaffected_by_keyword_matches() -> None:
    # A chunk with a strong keyword match but a low vector similarity score —
    # with hybrid search off, only the vector score should matter.
    rows = [
        FakeChunkRow(
            1, "guide.pdf", 0, "Exact error code ERR_CONNECTION_REFUSED appears here.",
            0.20, workspace_id=WORKSPACE_ID, keyword_rank_score=0.9,
        ),
        FakeChunkRow(2, "other.pdf", 0, "Something else entirely.", 0.85, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
        hybrid_search_enabled=False,
    )

    results = await retrieval_service.search("ERR_CONNECTION_REFUSED", workspace_id=WORKSPACE_ID)

    assert [r.document_id for r in results] == [2, 1]


@pytest.mark.asyncio
async def test_hybrid_search_promotes_a_strong_keyword_match_over_pure_vector_order() -> None:
    rows = [
        FakeChunkRow(
            1, "guide.pdf", 0, "Exact error code ERR_CONNECTION_REFUSED appears here.",
            0.20, workspace_id=WORKSPACE_ID, keyword_rank_score=0.9,
        ),
        FakeChunkRow(2, "other.pdf", 0, "Something else entirely.", 0.85, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
        hybrid_search_enabled=True,
    )

    results = await retrieval_service.search("ERR_CONNECTION_REFUSED", workspace_id=WORKSPACE_ID)

    # Ranked #1 in vector search (document 2) vs. ranked #1 in keyword search
    # (document 1) — RRF gives both an equal top-rank contribution, and
    # document 1 additionally still has a (smaller) vector-side contribution,
    # so it comes out on top under fusion even though pure vector order
    # would have put document 2 first.
    assert results[0].document_id == 1


@pytest.mark.asyncio
async def test_hybrid_search_respects_workspace_isolation() -> None:
    rows = [
        FakeChunkRow(
            1, "other-workspace.pdf", 0, "ERR_CONNECTION_REFUSED here too.",
            0.99, workspace_id=999, keyword_rank_score=0.99,
        ),
        FakeChunkRow(2, "mine.pdf", 0, "My own unrelated document.", 0.30, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
        hybrid_search_enabled=True,
    )

    results = await retrieval_service.search("ERR_CONNECTION_REFUSED", workspace_id=WORKSPACE_ID)

    assert [r.document_id for r in results] == [2]
