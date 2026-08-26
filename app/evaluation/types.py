"""Shared types for RAG evaluation."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvalCase:
    """One labeled evaluation case: a question with its known-correct answer."""

    question: str
    workspace_id: int
    # Document ids that a good retrieval should surface for this question.
    # Used for the mechanical retrieval metrics (hit rate, MRR, recall/precision@k) -
    # these require no LLM and are fully deterministic given a fixed corpus.
    relevant_document_ids: list[int]
    # A short phrase the final answer is expected to contain, for a cheap,
    # deterministic sanity check. Optional.
    expected_answer_contains: str | None = None
    # Free-text label for grouping/reporting (e.g. the source document's topic).
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalCaseResult:
    """Retrieval metrics for a single evaluated case."""

    case: EvalCase
    retrieved_document_ids: list[int]
    hit: bool
    reciprocal_rank: float
    recall_at_k: float
    precision_at_k: float


@dataclass(frozen=True)
class RetrievalEvalReport:
    """Aggregate retrieval metrics across every evaluated case."""

    case_results: list[RetrievalCaseResult]
    k: int

    @property
    def hit_rate(self) -> float:
        return _average(r.hit for r in self.case_results)

    @property
    def mean_reciprocal_rank(self) -> float:
        return _average(r.reciprocal_rank for r in self.case_results)

    @property
    def mean_recall_at_k(self) -> float:
        return _average(r.recall_at_k for r in self.case_results)

    @property
    def mean_precision_at_k(self) -> float:
        return _average(r.precision_at_k for r in self.case_results)


@dataclass(frozen=True)
class GenerationCaseResult:
    """Generation-quality judgments for a single evaluated case, from an LLM judge."""

    case: EvalCase
    answer: str
    faithfulness: float  # 0..1: is the answer supported by the retrieved context?
    answer_relevancy: float  # 0..1: does the answer actually address the question?
    contains_expected_phrase: bool | None  # None when the case set no expectation


@dataclass(frozen=True)
class GenerationEvalReport:
    """Aggregate generation-quality metrics across every evaluated case."""

    case_results: list[GenerationCaseResult]

    @property
    def mean_faithfulness(self) -> float:
        return _average(r.faithfulness for r in self.case_results)

    @property
    def mean_answer_relevancy(self) -> float:
        return _average(r.answer_relevancy for r in self.case_results)


def _average(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)
