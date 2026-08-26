"""Retrieval-Augmented Generation pipeline: retrieve context, then ask the LLM to answer.

Question -> Retrieval -> Answer -> (optional) Groundedness check -> Citations.
"""
import re
import time
from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import ChatProviderError
from app.core.logging import get_logger
from app.providers.base_chat_provider import ChatProvider
from app.schemas.rag import AskResponse, SourceItem
from app.services.retrieval_service import RetrievalService

logger = get_logger(__name__)

NO_CONTEXT_ANSWER = "Yüklenen belgelerde bu soruyu cevaplamak için yeterli bilgi bulunamadı."
UNGROUNDED_ANSWER = (
    "Üretilen cevap kaynak belgelerce yeterince desteklenmediği için gösterilemiyor. "
    "Lütfen soruyu farklı şekilde sormayı deneyin."
)

_CITATION_MARKER_PATTERN = re.compile(r"\[(\d+)\]")

SYSTEM_PROMPT = (
    "You are a careful knowledge assistant. Answer the user's question using ONLY the "
    "context excerpts provided below. Do not use any outside knowledge and do not make "
    "assumptions beyond what the context states. Cite the source of every factual claim "
    "inline, using the bracketed number shown before that excerpt exactly as given (e.g. "
    "[1]) — never invent a number that wasn't shown to you. Prior conversation turns are "
    "given only to help you understand what the user is referring to (e.g. 'it', 'that "
    "policy') — never treat them as a source of facts by themselves. If the context does "
    "not contain enough information to answer the question, respond in Turkish exactly "
    f"with: '{NO_CONTEXT_ANSWER}'. Otherwise, answer in the same language as the "
    "question, concisely and accurately, with inline citations."
)


class GroundednessChecker(Protocol):
    """Anything that can judge whether an answer's claims are supported by context.

    Satisfied structurally by `app.evaluation.generation_evaluator.GenerationEvaluator`
    (used both here, live, and offline by `scripts/run_rag_evaluation.py`) — RagService
    only depends on this interface.
    """

    async def score_faithfulness(self, context: str, answer: str) -> float: ...


@dataclass(frozen=True)
class HistoryTurn:
    """One prior turn of a conversation, fed back into the prompt for context."""

    role: str
    content: str


class RagService:
    """Combines semantic retrieval with an LLM chat completion to answer questions."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        chat_provider: ChatProvider,
        groundedness_checker: GroundednessChecker | None = None,
        groundedness_threshold: float = 0.5,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._chat_provider = chat_provider
        self._groundedness_checker = groundedness_checker
        self._groundedness_threshold = groundedness_threshold

    def _build_prompt(self, question: str, chunks: list, history: list[HistoryTurn]) -> str:
        context_blocks = "\n\n".join(
            f"[Source {i + 1} — {chunk.filename}, chunk {chunk.chunk_index}]\n{chunk.content}"
            for i, chunk in enumerate(chunks)
        )
        parts = []
        if history:
            history_text = "\n".join(f"{turn.role}: {turn.content}" for turn in history)
            parts.append(f"Previous conversation:\n{history_text}")
        parts.append(f"Context:\n{context_blocks}")
        parts.append(f"Question: {question}\n\nAnswer:")
        return "\n\n".join(parts)

    async def ask(
        self,
        question: str,
        workspace_id: int,
        history: list[HistoryTurn] | None = None,
        user_id: int | None = None,
    ) -> AskResponse:
        total_started_at = time.perf_counter()
        question = question.strip()

        retrieval_started_at = time.perf_counter()
        chunks = await self._retrieval_service.search(question, workspace_id=workspace_id)
        retrieval_duration_ms = round((time.perf_counter() - retrieval_started_at) * 1000, 2)

        log_fields = {
            "event": "rag_request",
            "user_id": user_id,
            "workspace_id": workspace_id,
            "provider": self._chat_provider.provider_name,
            "model": self._chat_provider.model,
            "retrieved_chunk_count": len(chunks),
            "retrieval_duration_ms": retrieval_duration_ms,
        }

        if not chunks:
            log_fields["generation_duration_ms"] = 0
            log_fields["total_duration_ms"] = round((time.perf_counter() - total_started_at) * 1000, 2)
            log_fields["success"] = True
            log_fields["grounded"] = False
            logger.info("RAG request completed with no relevant context", extra=log_fields)
            return AskResponse(answer=NO_CONTEXT_ANSWER, sources=[], grounded=None)

        prompt = self._build_prompt(question, chunks, history or [])
        generation_started_at = time.perf_counter()
        try:
            answer = await self._chat_provider.complete(SYSTEM_PROMPT, prompt)
        except Exception as exc:
            log_fields["generation_duration_ms"] = round((time.perf_counter() - generation_started_at) * 1000, 2)
            log_fields["total_duration_ms"] = round((time.perf_counter() - total_started_at) * 1000, 2)
            log_fields["success"] = False
            logger.warning("RAG request failed during generation", extra=log_fields)
            raise ChatProviderError(f"Failed to generate an answer: {exc}") from exc

        answer = answer.strip() or NO_CONTEXT_ANSWER
        log_fields["generation_duration_ms"] = round((time.perf_counter() - generation_started_at) * 1000, 2)

        grounded: bool | None = None
        if self._groundedness_checker is not None:
            groundedness_started_at = time.perf_counter()
            context_text = "\n\n".join(chunk.content for chunk in chunks)
            try:
                groundedness_score = await self._groundedness_checker.score_faithfulness(context_text, answer)
                grounded = groundedness_score >= self._groundedness_threshold
            except Exception:
                # A judge failure must not take the whole answer down with it —
                # log it and fall through treating the answer as ungraded, not ungrounded.
                logger.warning("Groundedness check failed; skipping it for this request.")
                groundedness_score = None
            log_fields["groundedness_duration_ms"] = round(
                (time.perf_counter() - groundedness_started_at) * 1000, 2
            )
            log_fields["groundedness_score"] = groundedness_score

            if grounded is False:
                log_fields["total_duration_ms"] = round((time.perf_counter() - total_started_at) * 1000, 2)
                log_fields["success"] = True
                log_fields["grounded"] = False
                logger.info("RAG request completed but answer failed the groundedness check", extra=log_fields)
                return AskResponse(answer=UNGROUNDED_ANSWER, sources=[], grounded=False)

        log_fields["total_duration_ms"] = round((time.perf_counter() - total_started_at) * 1000, 2)
        log_fields["success"] = True
        log_fields["grounded"] = grounded if grounded is not None else True
        logger.info("RAG request completed", extra=log_fields)

        cited_markers = {int(marker) for marker in _CITATION_MARKER_PATTERN.findall(answer)}
        sources = [
            SourceItem(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                similarity_score=chunk.similarity_score,
                content=chunk.content,
                citation_marker=i + 1,
                cited=(i + 1) in cited_markers,
            )
            for i, chunk in enumerate(chunks)
        ]
        return AskResponse(answer=answer, sources=sources, grounded=grounded)
