"""Tests for CrossEncoderRerankingService, with the actual model mocked out.

Loading a real sentence-transformers model requires a network download and a
non-trivial amount of time - exactly what this project's test suite has
avoided everywhere else (see tests/fakes.py) - so these tests monkeypatch
`_load_model` with a deterministic fake that mimics CrossEncoder's
`.predict(pairs) -> list[float]` interface, and verify the surrounding logic
(sigmoid normalization, sorting, truncation, empty input) directly.
"""
import pytest

from app.services import cross_encoder_reranking_service as module
from app.services.cross_encoder_reranking_service import CrossEncoderRerankingService
from app.services.retrieval_types import RetrievedChunk


def _chunk(document_id: int, content: str, similarity_score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=document_id,
        filename=f"doc-{document_id}.txt",
        chunk_index=0,
        content=content,
        similarity_score=similarity_score,
    )


class _FakeCrossEncoder:
    """Mimics sentence_transformers.CrossEncoder's predict() interface."""

    def __init__(self, scores_by_content: dict[str, float]) -> None:
        self._scores_by_content = scores_by_content

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [self._scores_by_content[content] for _query, content in pairs]


@pytest.fixture(autouse=True)
def _clear_model_cache() -> None:
    # _load_model is process-wide lru_cache'd by model name - clear it so one
    # test's monkeypatched model never leaks into another.
    module._load_model.cache_clear()
    yield
    module._load_model.cache_clear()


def test_rerank_returns_empty_list_for_no_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "_load_model", lambda model_name: _FakeCrossEncoder({}))
    service = CrossEncoderRerankingService()

    assert service.rerank("anything", [], top_k=5) == []


def test_rerank_orders_by_model_score_descending(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = _FakeCrossEncoder({"low relevance chunk": -5.0, "high relevance chunk": 5.0})
    monkeypatch.setattr(module, "_load_model", lambda model_name: fake_model)
    service = CrossEncoderRerankingService()
    candidates = [
        _chunk(1, "low relevance chunk", similarity_score=0.99),
        _chunk(2, "high relevance chunk", similarity_score=0.10),
    ]

    result = service.rerank("query", candidates, top_k=2)

    # The cross-encoder's judgment overrides raw vector similarity entirely.
    assert [c.document_id for c in result] == [2, 1]


def test_rerank_squashes_raw_logits_into_a_0_to_1_range(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = _FakeCrossEncoder({"strong match": 10.0, "weak match": -10.0})
    monkeypatch.setattr(module, "_load_model", lambda model_name: fake_model)
    service = CrossEncoderRerankingService()
    candidates = [_chunk(1, "strong match"), _chunk(2, "weak match")]

    result = service.rerank("query", candidates, top_k=2)

    for chunk in result:
        assert 0.0 <= chunk.similarity_score <= 1.0
    assert result[0].similarity_score > 0.99
    assert result[1].similarity_score < 0.01


def test_rerank_truncates_to_top_k(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = _FakeCrossEncoder({f"chunk {i}": float(i) for i in range(10)})
    monkeypatch.setattr(module, "_load_model", lambda model_name: fake_model)
    service = CrossEncoderRerankingService()
    candidates = [_chunk(i, f"chunk {i}") for i in range(10)]

    result = service.rerank("query", candidates, top_k=3)

    assert len(result) == 3
    # Highest-scored chunks (9, 8, 7) win.
    assert [c.document_id for c in result] == [9, 8, 7]
