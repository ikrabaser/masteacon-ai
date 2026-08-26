"""Runs a set of labeled EvalCases through a real RetrievalService and scores
the results with the mechanical metrics in retrieval_metrics.py.

No LLM is involved — this only measures whether the *retrieval* stage (vector
search, hybrid search, reranking, query rewriting, in whatever combination is
currently configured) surfaces the documents a human labeled as relevant for
each question, not whether any answer generated from them would be good.
"""
from app.evaluation.retrieval_metrics import hit, precision_at_k, recall_at_k, reciprocal_rank
from app.evaluation.types import EvalCase, RetrievalCaseResult, RetrievalEvalReport
from app.services.retrieval_service import RetrievalService


class RetrievalEvaluator:
    """Evaluates RetrievalService against a set of labeled cases."""

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service

    async def evaluate(self, cases: list[EvalCase], k: int = 5) -> RetrievalEvalReport:
        case_results = [await self._evaluate_case(case, k) for case in cases]
        return RetrievalEvalReport(case_results=case_results, k=k)

    async def _evaluate_case(self, case: EvalCase, k: int) -> RetrievalCaseResult:
        chunks = await self._retrieval_service.search(case.question, workspace_id=case.workspace_id, limit=k)
        # A document can appear via multiple chunks — dedupe while preserving
        # the order chunks were returned in (best match first), since rank
        # matters for reciprocal_rank.
        retrieved_document_ids: list[int] = []
        for chunk in chunks:
            if chunk.document_id not in retrieved_document_ids:
                retrieved_document_ids.append(chunk.document_id)

        relevant_document_ids = set(case.relevant_document_ids)
        return RetrievalCaseResult(
            case=case,
            retrieved_document_ids=retrieved_document_ids,
            hit=hit(retrieved_document_ids, relevant_document_ids),
            reciprocal_rank=reciprocal_rank(retrieved_document_ids, relevant_document_ids),
            recall_at_k=recall_at_k(retrieved_document_ids, relevant_document_ids),
            precision_at_k=precision_at_k(retrieved_document_ids, relevant_document_ids),
        )
