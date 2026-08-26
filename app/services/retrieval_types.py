"""Shared retrieval data types — split out so RetrievalService and the various
reranking implementations can all depend on RetrievedChunk without an import
cycle between them.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved chunk paired with its similarity score and parent document metadata."""

    document_id: int
    filename: str
    chunk_index: int
    content: str
    similarity_score: float


class Reranker(Protocol):
    """Anything that can reorder+truncate retrieval candidates by relevance.

    Implemented by both RerankingService (lexical overlap, no dependencies)
    and CrossEncoderRerankingService (a local ML model) — RetrievalService
    only ever depends on this interface, never a concrete implementation.
    """

    def rerank(self, query: str, candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]: ...
