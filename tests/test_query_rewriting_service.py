"""Tests for QueryRewritingService."""
import pytest

from app.services.query_rewriting_service import QueryRewritingService
from tests.fakes import FakeChatProvider


@pytest.mark.asyncio
async def test_rewrite_returns_the_chat_provider_response() -> None:
    provider = FakeChatProvider(answer="Docker daemon connection errors, compose startup failure")
    service = QueryRewritingService(provider)

    result = await service.rewrite("docker neden olmuyor")

    assert result == "Docker daemon connection errors, compose startup failure"
    assert provider.last_user_prompt == "docker neden olmuyor"


@pytest.mark.asyncio
async def test_rewrite_strips_surrounding_whitespace() -> None:
    provider = FakeChatProvider(answer="  rewritten query  \n")
    service = QueryRewritingService(provider)

    result = await service.rewrite("original question")

    assert result == "rewritten query"


@pytest.mark.asyncio
async def test_rewrite_falls_back_to_original_question_on_provider_failure() -> None:
    provider = FakeChatProvider(raise_on_complete=RuntimeError("provider is down"))
    service = QueryRewritingService(provider)

    result = await service.rewrite("what is the leave policy?")

    assert result == "what is the leave policy?"


@pytest.mark.asyncio
async def test_rewrite_falls_back_to_original_question_on_empty_response() -> None:
    provider = FakeChatProvider(answer="   ")
    service = QueryRewritingService(provider)

    result = await service.rewrite("what is the leave policy?")

    assert result == "what is the leave policy?"


@pytest.mark.asyncio
async def test_rewrite_returns_empty_string_unchanged_for_empty_question() -> None:
    provider = FakeChatProvider(answer="should never be called")
    service = QueryRewritingService(provider)

    result = await service.rewrite("   ")

    assert result == ""
    assert provider.last_user_prompt is None
