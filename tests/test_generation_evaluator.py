"""Tests for GenerationEvaluator's prompt-building and response-parsing logic.

The real judge call requires a live LLM (real, billable, non-deterministic) -
never something a unit test should depend on - so these use FakeChatProvider
with a canned response instead, verifying that GenerationEvaluator sends the
right prompt and correctly parses (or gracefully degrades on) the response.
"""
import pytest

from app.evaluation.generation_evaluator import GenerationEvaluator
from tests.fakes import FakeChatProvider


@pytest.mark.asyncio
async def test_score_faithfulness_parses_a_well_formed_json_response() -> None:
    provider = FakeChatProvider(answer='{"score": 0.85, "reason": "mostly supported"}')
    evaluator = GenerationEvaluator(provider)

    score = await evaluator.score_faithfulness("context text", "answer text")

    assert score == 0.85
    assert "context text" in provider.last_user_prompt
    assert "answer text" in provider.last_user_prompt


@pytest.mark.asyncio
async def test_score_answer_relevancy_parses_a_well_formed_json_response() -> None:
    provider = FakeChatProvider(answer='{"score": 0.4, "reason": "partially on-topic"}')
    evaluator = GenerationEvaluator(provider)

    score = await evaluator.score_answer_relevancy("the question", "the answer")

    assert score == 0.4
    assert "the question" in provider.last_user_prompt


@pytest.mark.asyncio
async def test_score_falls_back_to_extracting_a_number_from_prose() -> None:
    # Some models wrap JSON in prose despite instructions not to.
    provider = FakeChatProvider(answer='Sure! Here is my grade: {"score": 0.7} - hope that helps.')
    evaluator = GenerationEvaluator(provider)

    # The prose wrapper breaks strict JSON parsing, but a number is still
    # recoverable via the fallback regex.
    score = await evaluator.score_faithfulness("context", "answer")

    assert score == 0.7


@pytest.mark.asyncio
async def test_score_defaults_to_zero_when_nothing_parseable_is_found() -> None:
    provider = FakeChatProvider(answer="I refuse to grade this.")
    evaluator = GenerationEvaluator(provider)

    score = await evaluator.score_faithfulness("context", "answer")

    assert score == 0.0


@pytest.mark.asyncio
async def test_score_is_clamped_to_the_0_to_1_range() -> None:
    provider = FakeChatProvider(answer='{"score": 5.0}')
    evaluator = GenerationEvaluator(provider)

    score = await evaluator.score_faithfulness("context", "answer")

    assert score == 1.0
