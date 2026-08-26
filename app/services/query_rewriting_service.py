"""Rewrites a user's raw question into a retrieval-optimized query.

Question -> Query Rewriter -> Retrieval. Users often phrase questions
informally or too tersely for embedding/keyword search to match well against
formally-written documents — e.g. "docker neden olmuyor" retrieves worse than
"Docker container fails to start, Docker daemon connection errors, compose
startup failure" would. This rewrite is retrieval-only: the *original*
question is still what gets shown to the user and answered by the LLM at
generation time (see RagService) — rewriting only changes what text is
embedded/keyword-searched to find candidate chunks.
"""
from app.core.logging import get_logger
from app.providers.base_chat_provider import ChatProvider

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You rewrite a user's question into a short, explicit search query optimized for "
    "retrieving relevant passages from a document collection via semantic and keyword "
    "search. Expand abbreviations, informal phrasing, and vague references into concrete "
    "terms that are likely to appear in relevant documents. Do not answer the question. "
    "Do not add facts or assumptions that aren't implied by the question itself. Respond "
    "with ONLY the rewritten query, nothing else — no preamble, no quotes."
)


class QueryRewritingService:
    """Rewrites a question into a retrieval-optimized query via a chat provider."""

    def __init__(self, chat_provider: ChatProvider) -> None:
        self._chat_provider = chat_provider

    async def rewrite(self, question: str) -> str:
        question = question.strip()
        if not question:
            return question

        try:
            rewritten = await self._chat_provider.complete(SYSTEM_PROMPT, question)
        except Exception:
            # Retrieval must never fail just because the rewrite call did —
            # fall back to searching with the original question unchanged.
            logger.warning("Query rewriting failed; falling back to the original question.")
            return question

        rewritten = rewritten.strip()
        return rewritten or question
