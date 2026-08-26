"""A real second-stage reranker, backed by a local cross-encoder model.

Unlike RerankingService's lexical-overlap heuristic, a cross-encoder reads the
query and each candidate chunk *together* through a small transformer and
outputs a single relevance score — this generally judges semantic relevance
far more accurately than comparing embeddings or token sets independently,
because the model can directly attend across both texts.

Runs entirely locally (no external API call, no added per-query network cost)
via `sentence-transformers`, after the model has been downloaded once. The
default model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) is small (~80MB) and
fast enough to rerank a few dozen candidates in well under a second on CPU.
"""
import math
from dataclasses import replace
from functools import lru_cache

from app.services.retrieval_types import RetrievedChunk

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    # Cached process-wide: loading a transformer model is expensive (disk read
    # + memory), and every request would otherwise reload it from scratch.
    # Imported lazily so importing this module (e.g. at app startup, or in
    # tests that never construct a CrossEncoderRerankingService) doesn't pull
    # in torch unless the cross-encoder reranker is actually used.
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class CrossEncoderRerankingService:
    """Reranks retrieved chunks using a local cross-encoder model."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self._model_name = model_name

    def rerank(self, query: str, candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        if not candidates:
            return []

        model = _load_model(self._model_name)
        pairs = [(query, candidate.content) for candidate in candidates]
        raw_scores = model.predict(pairs)

        # ms-marco cross-encoders output an unbounded relevance logit, not a
        # 0..1 score — squash it through a sigmoid so `similarity_score` keeps
        # the same "higher is better, roughly 0..1" meaning callers/API
        # responses already expect from vector cosine similarity.
        scored = sorted(
            (
                replace(candidate, similarity_score=round(_sigmoid(float(raw_score)), 4))
                for candidate, raw_score in zip(candidates, raw_scores)
            ),
            key=lambda chunk: chunk.similarity_score,
            reverse=True,
        )
        return scored[:top_k]
