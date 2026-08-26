"""Tests for get_reranking_service's provider selection (RERANKER_PROVIDER)."""
import pytest

from app.api.dependencies import UnsupportedRerankerProviderError, get_reranking_service
from app.core.config import Settings
from app.services.cross_encoder_reranking_service import CrossEncoderRerankingService
from app.services.reranking_service import RerankingService


def _settings(**overrides) -> Settings:
    defaults = {"rerank_enabled": True, "reranker_provider": "lexical"}
    defaults.update(overrides)
    return Settings(**defaults)


def test_returns_none_when_reranking_disabled() -> None:
    assert get_reranking_service(_settings(rerank_enabled=False)) is None


def test_returns_lexical_reranker_by_default() -> None:
    service = get_reranking_service(_settings())

    assert isinstance(service, RerankingService)


def test_returns_cross_encoder_reranker_when_configured() -> None:
    service = get_reranking_service(_settings(reranker_provider="cross_encoder"))

    assert isinstance(service, CrossEncoderRerankingService)


def test_is_case_insensitive() -> None:
    service = get_reranking_service(_settings(reranker_provider="CROSS_ENCODER"))

    assert isinstance(service, CrossEncoderRerankingService)


def test_rejects_unknown_provider() -> None:
    with pytest.raises(UnsupportedRerankerProviderError):
        get_reranking_service(_settings(reranker_provider="some-other-reranker"))
