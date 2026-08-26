"""Tests for RagService using fake retrieval/chat providers."""
import pytest

from app.services.embedding_service import EmbeddingService
from app.services.rag_service import NO_CONTEXT_ANSWER, UNGROUNDED_ANSWER, RagService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeChatProvider, FakeChunkRepository, FakeChunkRow, FakeEmbeddingProvider

WORKSPACE_ID = 1


def _build_rag_service(
    rows: list[FakeChunkRow],
    answer: str = "The annual leave is 14 days.",
    groundedness_checker=None,
    groundedness_threshold: float = 0.5,
) -> tuple[RagService, FakeChatProvider]:
    retrieval_service = RetrievalService(
        chunk_repository=FakeChunkRepository(rows),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        default_top_k=5,
        similarity_threshold=0.3,
    )
    chat_provider = FakeChatProvider(answer=answer)
    return (
        RagService(
            retrieval_service=retrieval_service,
            chat_provider=chat_provider,
            groundedness_checker=groundedness_checker,
            groundedness_threshold=groundedness_threshold,
        ),
        chat_provider,
    )


@pytest.mark.asyncio
async def test_ask_returns_answer_with_sources_when_context_found() -> None:
    rows = [FakeChunkRow(1, "handbook.pdf", 4, "Annual leave policy is 14 days.", 0.91)]
    rag_service, chat_provider = _build_rag_service(rows)

    response = await rag_service.ask("What is the annual leave policy?", workspace_id=WORKSPACE_ID)

    assert response.answer == "The annual leave is 14 days."
    assert len(response.sources) == 1
    assert response.sources[0].filename == "handbook.pdf"
    assert response.sources[0].document_id == 1
    assert response.sources[0].content == "Annual leave policy is 14 days."
    assert chat_provider.last_user_prompt is not None
    assert "Annual leave policy is 14 days." in chat_provider.last_user_prompt


@pytest.mark.asyncio
async def test_ask_returns_fallback_answer_when_no_context() -> None:
    rag_service, chat_provider = _build_rag_service([])

    response = await rag_service.ask("What is the meaning of life?", workspace_id=WORKSPACE_ID)

    assert response.answer == NO_CONTEXT_ANSWER
    assert response.sources == []
    assert response.grounded is None
    # The chat provider must not be called when there is no retrieved context.
    assert chat_provider.last_user_prompt is None


@pytest.mark.asyncio
async def test_ask_marks_a_source_as_cited_when_the_answer_references_its_marker() -> None:
    rows = [
        FakeChunkRow(1, "a.pdf", 0, "First fact.", 0.9),
        FakeChunkRow(2, "b.pdf", 0, "Second fact.", 0.8),
    ]
    rag_service, _ = _build_rag_service(rows, answer="The answer cites the first source [1].")

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.sources[0].citation_marker == 1
    assert response.sources[0].cited is True
    assert response.sources[1].citation_marker == 2
    assert response.sources[1].cited is False


@pytest.mark.asyncio
async def test_ask_marks_no_sources_cited_when_answer_has_no_citation_markers() -> None:
    rows = [FakeChunkRow(1, "a.pdf", 0, "Some fact.", 0.9)]
    rag_service, _ = _build_rag_service(rows, answer="An answer with no citations at all.")

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.sources[0].cited is False


@pytest.mark.asyncio
async def test_ask_grounded_is_none_when_groundedness_check_is_disabled() -> None:
    rows = [FakeChunkRow(1, "a.pdf", 0, "Some fact.", 0.9)]
    rag_service, _ = _build_rag_service(rows)  # no groundedness_checker

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.grounded is None
    assert response.answer == "The annual leave is 14 days."


class _FixedGroundednessChecker:
    """A GroundednessChecker test double that always returns a fixed score."""

    def __init__(self, score: float | None = None, raise_error: bool = False) -> None:
        self.score = score
        self.raise_error = raise_error
        self.last_context: str | None = None
        self.last_answer: str | None = None

    async def score_faithfulness(self, context: str, answer: str) -> float:
        self.last_context = context
        self.last_answer = answer
        if self.raise_error:
            raise RuntimeError("judge is down")
        return self.score


@pytest.mark.asyncio
async def test_ask_passes_through_answer_when_groundedness_check_passes() -> None:
    rows = [FakeChunkRow(1, "a.pdf", 0, "Some fact.", 0.9)]
    checker = _FixedGroundednessChecker(score=0.9)
    rag_service, _ = _build_rag_service(rows, groundedness_checker=checker, groundedness_threshold=0.5)

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.grounded is True
    assert response.answer == "The annual leave is 14 days."
    assert len(response.sources) == 1
    assert checker.last_answer == "The annual leave is 14 days."


@pytest.mark.asyncio
async def test_ask_replaces_answer_when_groundedness_check_fails() -> None:
    rows = [FakeChunkRow(1, "a.pdf", 0, "Some fact.", 0.9)]
    checker = _FixedGroundednessChecker(score=0.1)
    rag_service, _ = _build_rag_service(rows, groundedness_checker=checker, groundedness_threshold=0.5)

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.grounded is False
    assert response.answer == UNGROUNDED_ANSWER
    assert response.sources == []


@pytest.mark.asyncio
async def test_ask_score_exactly_at_threshold_counts_as_grounded() -> None:
    rows = [FakeChunkRow(1, "a.pdf", 0, "Some fact.", 0.9)]
    checker = _FixedGroundednessChecker(score=0.5)
    rag_service, _ = _build_rag_service(rows, groundedness_checker=checker, groundedness_threshold=0.5)

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.grounded is True


@pytest.mark.asyncio
async def test_ask_treats_a_failed_groundedness_check_as_ungraded_not_ungrounded() -> None:
    # A judge failure must not take the whole answer down with it.
    rows = [FakeChunkRow(1, "a.pdf", 0, "Some fact.", 0.9)]
    checker = _FixedGroundednessChecker(raise_error=True)
    rag_service, _ = _build_rag_service(rows, groundedness_checker=checker, groundedness_threshold=0.5)

    response = await rag_service.ask("question", workspace_id=WORKSPACE_ID)

    assert response.grounded is None
    assert response.answer == "The annual leave is 14 days."
    assert len(response.sources) == 1
