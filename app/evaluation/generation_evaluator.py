"""LLM-judge based generation-quality scoring: Faithfulness and Answer Relevancy.

Unlike the mechanical retrieval metrics, these require a language model to
actually read the question/context/answer and judge them — there's no
dependency-free way to check "is this claim actually supported by the
context" or "does this answer address what was asked." Each judgment costs a
real LLM call (via the same ChatProvider the app already uses elsewhere), so
this is opt-in and never run as part of the pytest suite — see
tests/test_generation_evaluator.py, which mocks the judge's response instead
of making a real call, to keep judgment logic testable without needing an API
key in CI.
"""
import json
import re

from app.core.logging import get_logger
from app.providers.base_chat_provider import ChatProvider

logger = get_logger(__name__)

FAITHFULNESS_SYSTEM_PROMPT = (
    "You are a strict grader. Given a CONTEXT and an ANSWER, judge whether every "
    "factual claim in the ANSWER is directly supported by the CONTEXT. An answer "
    'that says it could not find enough information should score 1.0 if the '
    "context genuinely lacks that information, or 0.0 if the context did contain "
    'it and the answer wrongly claimed otherwise. Respond with ONLY a JSON object: '
    '{"score": <float 0.0-1.0>, "reason": "<one short sentence>"}.'
)

ANSWER_RELEVANCY_SYSTEM_PROMPT = (
    "You are a strict grader. Given a QUESTION and an ANSWER, judge whether the "
    "ANSWER actually addresses what was asked — not whether it's factually correct, "
    'just whether it is on-topic and responsive to the question. Respond with ONLY '
    'a JSON object: {"score": <float 0.0-1.0>, "reason": "<one short sentence>"}.'
)


def _parse_score(raw_response: str) -> float:
    try:
        payload = json.loads(raw_response.strip())
        score = float(payload["score"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Be lenient: some models wrap JSON in prose despite instructions —
        # fall back to pulling the first number out of the text.
        match = re.search(r"(\d+(?:\.\d+)?)", raw_response)
        if not match:
            logger.warning("Could not parse a judge score from the response; defaulting to 0.0.")
            return 0.0
        score = float(match.group(1))
    return max(0.0, min(1.0, score))


class GenerationEvaluator:
    """LLM-judge scoring for Faithfulness and Answer Relevancy."""

    def __init__(self, chat_provider: ChatProvider) -> None:
        self._chat_provider = chat_provider

    async def score_faithfulness(self, context: str, answer: str) -> float:
        user_prompt = f"CONTEXT:\n{context}\n\nANSWER:\n{answer}"
        response = await self._chat_provider.complete(FAITHFULNESS_SYSTEM_PROMPT, user_prompt)
        return _parse_score(response)

    async def score_answer_relevancy(self, question: str, answer: str) -> float:
        user_prompt = f"QUESTION:\n{question}\n\nANSWER:\n{answer}"
        response = await self._chat_provider.complete(ANSWER_RELEVANCY_SYSTEM_PROMPT, user_prompt)
        return _parse_score(response)
