"""Tests for the mechanical (LLM-free) retrieval evaluation metrics."""
from app.evaluation.retrieval_metrics import hit, precision_at_k, recall_at_k, reciprocal_rank


def test_hit_true_when_any_relevant_document_is_retrieved() -> None:
    assert hit([5, 1, 9], {1, 2}) is True


def test_hit_false_when_no_relevant_document_is_retrieved() -> None:
    assert hit([5, 9], {1, 2}) is False


def test_hit_false_for_empty_retrieval() -> None:
    assert hit([], {1, 2}) is False


def test_reciprocal_rank_is_one_when_first_result_is_relevant() -> None:
    assert reciprocal_rank([1, 5, 9], {1}) == 1.0


def test_reciprocal_rank_is_one_half_when_second_result_is_relevant() -> None:
    assert reciprocal_rank([5, 1, 9], {1}) == 0.5


def test_reciprocal_rank_is_zero_when_nothing_relevant_is_retrieved() -> None:
    assert reciprocal_rank([5, 9], {1}) == 0.0


def test_recall_at_k_counts_fraction_of_relevant_documents_found() -> None:
    # 2 of 4 relevant documents were retrieved.
    assert recall_at_k([1, 2, 8, 9], {1, 2, 3, 4}) == 0.5


def test_recall_at_k_is_zero_when_there_are_no_relevant_documents() -> None:
    assert recall_at_k([1, 2], set()) == 0.0


def test_recall_at_k_does_not_double_count_duplicate_retrievals() -> None:
    assert recall_at_k([1, 1, 1], {1, 2}) == 0.5


def test_precision_at_k_counts_fraction_of_retrieved_documents_that_are_relevant() -> None:
    # 1 of 4 retrieved documents was actually relevant.
    assert precision_at_k([1, 8, 9, 10], {1, 2}) == 0.25


def test_precision_at_k_is_zero_for_empty_retrieval() -> None:
    assert precision_at_k([], {1, 2}) == 0.0
