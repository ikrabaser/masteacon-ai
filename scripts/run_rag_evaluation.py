"""CLI tool: runs a labeled evaluation dataset against a real database (and,
optionally, a real LLM) to measure retrieval and generation quality.

Usage:
    python -m scripts.run_rag_evaluation eval_datasets/sample_eval.json
    python -m scripts.run_rag_evaluation eval_datasets/sample_eval.json --with-generation
    python -m scripts.run_rag_evaluation eval_datasets/sample_eval.json --k 5

Requires a running, migrated database with the workspace(s)/document(s)
referenced in the dataset already indexed. `--with-generation` additionally
requires a configured LLM provider API key and makes real (billable) API
calls — one per case for the answer, plus two more per case for the LLM-judge
scores.

This is a standalone script, not a web route: RAG evaluation is a
development/CI-adjacent quality check you run deliberately against a known
dataset, not something the running application does on its own.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.evaluation.generation_evaluator import GenerationEvaluator
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.types import EvalCase
from app.providers.chat_provider_factory import create_chat_provider
from app.providers.openai_provider import OpenAIEmbeddingProvider
from app.repositories.chunk_repository import ChunkRepository
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RagService
from app.services.reranking_service import RerankingService
from app.services.retrieval_service import RetrievalService


def _load_cases(path: Path) -> list[EvalCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalCase(
            question=c["question"],
            workspace_id=c["workspace_id"],
            relevant_document_ids=c["relevant_document_ids"],
            expected_answer_contains=c.get("expected_answer_contains"),
            tags=c.get("tags", []),
        )
        for c in raw_cases
    ]


async def _run(dataset_path: Path, k: int, with_generation: bool) -> int:
    settings = get_settings()
    cases = _load_cases(dataset_path)
    if not cases:
        print("No cases found in dataset.")
        return 1

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            chunk_repository = ChunkRepository(session)
            embedding_service = EmbeddingService(
                OpenAIEmbeddingProvider(api_key=settings.openai_api_key, model=settings.openai_embedding_model)
            )
            reranking_service = RerankingService() if settings.rerank_enabled else None

            retrieval_service = RetrievalService(
                chunk_repository=chunk_repository,
                embedding_service=embedding_service,
                default_top_k=settings.search_top_k,
                similarity_threshold=settings.similarity_threshold,
                reranking_service=reranking_service,
                candidate_count=settings.retrieval_candidate_count,
                rerank_top_k=settings.rerank_top_k,
                hybrid_search_enabled=settings.hybrid_search_enabled,
            )

            retrieval_report = await RetrievalEvaluator(retrieval_service).evaluate(cases, k=k)

            print(f"\n=== Retrieval evaluation ({len(cases)} cases, k={k}) ===")
            print(f"Hit rate:             {retrieval_report.hit_rate:.1%}")
            print(f"Mean Reciprocal Rank: {retrieval_report.mean_reciprocal_rank:.3f}")
            print(f"Mean Recall@{k}:         {retrieval_report.mean_recall_at_k:.1%}")
            print(f"Mean Precision@{k}:      {retrieval_report.mean_precision_at_k:.1%}")
            for result in retrieval_report.case_results:
                status = "HIT " if result.hit else "MISS"
                print(
                    f"  [{status}] {result.case.question!r} "
                    f"-> retrieved {result.retrieved_document_ids}, "
                    f"expected any of {result.case.relevant_document_ids}"
                )

            if not with_generation:
                return 0

            chat_provider = create_chat_provider(settings)
            rag_service = RagService(retrieval_service=retrieval_service, chat_provider=chat_provider)
            generation_evaluator = GenerationEvaluator(chat_provider)

            print(f"\n=== Generation evaluation ({len(cases)} cases, real LLM calls) ===")
            faithfulness_scores: list[float] = []
            relevancy_scores: list[float] = []
            for case in cases:
                chunks = await retrieval_service.search(case.question, workspace_id=case.workspace_id, limit=k)
                context = "\n\n".join(chunk.content for chunk in chunks)
                response = await rag_service.ask(case.question, workspace_id=case.workspace_id)

                faithfulness = await generation_evaluator.score_faithfulness(context, response.answer)
                relevancy = await generation_evaluator.score_answer_relevancy(case.question, response.answer)
                faithfulness_scores.append(faithfulness)
                relevancy_scores.append(relevancy)

                contains_note = ""
                if case.expected_answer_contains:
                    contained = case.expected_answer_contains.lower() in response.answer.lower()
                    contains_note = f", expected phrase {'found' if contained else 'MISSING'}"

                print(
                    f"  {case.question!r} -> faithfulness={faithfulness:.2f}, "
                    f"relevancy={relevancy:.2f}{contains_note}"
                )

            mean_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores)
            mean_relevancy = sum(relevancy_scores) / len(relevancy_scores)
            print(f"\nMean Faithfulness:      {mean_faithfulness:.1%}")
            print(f"Mean Answer Relevancy:  {mean_relevancy:.1%}")

            overall = (
                retrieval_report.hit_rate
                + retrieval_report.mean_reciprocal_rank
                + mean_faithfulness
                + mean_relevancy
            ) / 4
            print(f"\nOverall RAG evaluation score: {overall * 100:.0f}/100")
            return 0
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", type=Path, help="Path to a JSON eval dataset (see eval_datasets/sample_eval.json)")
    parser.add_argument("--k", type=int, default=5, help="Number of chunks to retrieve per question (default: 5)")
    parser.add_argument(
        "--with-generation",
        action="store_true",
        help="Also run generation (real, billable LLM calls: one answer + two judge calls per case)",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(_run(args.dataset, args.k, args.with_generation))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
