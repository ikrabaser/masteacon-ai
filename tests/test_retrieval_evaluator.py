"""Tests for RetrievalEvaluator, using fake repository/embedding provider —
no real database or LLM involved.
"""
import pytest

from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.types import EvalCase
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeChunkRepository, FakeChunkRow, FakeEmbeddingProvider

WORKSPACE_ID = 1


@pytest.mark.asyncio
async def test_evaluate_reports_a_hit_when_a_relevant_document_is_retrieved() -> None:
    rows = [
        FakeChunkRow(1, "handbook.pdf", 0, "Annual leave is 14 days.", 0.9, workspace_id=WORKSPACE_ID),
        FakeChunkRow(2, "other.pdf", 0, "Unrelated content.", 0.1, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )
    cases = [EvalCase(question="leave policy", workspace_id=WORKSPACE_ID, relevant_document_ids=[1])]

    report = await RetrievalEvaluator(retrieval_service).evaluate(cases, k=5)

    assert report.hit_rate == 1.0
    assert report.mean_reciprocal_rank == 1.0
    assert report.case_results[0].retrieved_document_ids[0] == 1


@pytest.mark.asyncio
async def test_evaluate_reports_a_miss_when_no_relevant_document_is_retrieved() -> None:
    rows = [FakeChunkRow(9, "unrelated.pdf", 0, "Nothing to do with leave.", 0.9, workspace_id=WORKSPACE_ID)]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )
    cases = [EvalCase(question="leave policy", workspace_id=WORKSPACE_ID, relevant_document_ids=[1])]

    report = await RetrievalEvaluator(retrieval_service).evaluate(cases, k=5)

    assert report.hit_rate == 0.0
    assert report.mean_reciprocal_rank == 0.0
    assert report.mean_recall_at_k == 0.0


@pytest.mark.asyncio
async def test_evaluate_averages_metrics_across_multiple_cases() -> None:
    rows = [
        FakeChunkRow(1, "a.pdf", 0, "relevant content one", 0.9, workspace_id=WORKSPACE_ID),
        FakeChunkRow(9, "b.pdf", 0, "irrelevant content", 0.9, workspace_id=WORKSPACE_ID),
    ]
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.0,
    )
    cases = [
        EvalCase(question="q1", workspace_id=WORKSPACE_ID, relevant_document_ids=[1]),  # hit
        EvalCase(question="q2", workspace_id=WORKSPACE_ID, relevant_document_ids=[404]),  # miss
    ]

    report = await RetrievalEvaluator(retrieval_service).evaluate(cases, k=5)

    assert len(report.case_results) == 2
    assert report.hit_rate == 0.5  # one hit, one miss
