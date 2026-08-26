"""Tests for the Reciprocal Rank Fusion (RRF) scoring function."""
from app.services.reciprocal_rank_fusion import reciprocal_rank_fusion_scores


def test_item_ranked_first_in_a_single_list_scores_highest() -> None:
    scores = reciprocal_rank_fusion_scores([["a", "b", "c"]])

    assert scores["a"] > scores["b"] > scores["c"]


def test_item_appearing_in_both_lists_outscores_an_item_in_only_one() -> None:
    scores = reciprocal_rank_fusion_scores([["a", "b"], ["b", "c"]])

    # "b" is ranked in both lists; "a" and "c" only rank in one each.
    assert scores["b"] > scores["a"]
    assert scores["b"] > scores["c"]


def test_top_rank_in_either_list_can_outrank_a_low_rank_in_both() -> None:
    # "a" is #1 in list one and absent from list two.
    # "z" is #10 in both lists.
    # With a small rrf_k, rank decays sharply enough that a single top rank
    # dominates two mediocre ones (with a large rrf_k, appearing in every
    # list starts to matter more than any single rank — both are legitimate
    # RRF behaviors depending on how rrf_k is tuned).
    list_one = ["a"] + [f"filler-{i}" for i in range(8)] + ["z"]
    list_two = [f"other-{i}" for i in range(9)] + ["z"]

    scores = reciprocal_rank_fusion_scores([list_one, list_two], rrf_k=1)

    assert scores["a"] > scores["z"]


def test_empty_lists_produce_empty_scores() -> None:
    assert reciprocal_rank_fusion_scores([[], []]) == {}


def test_single_empty_input_list_produces_empty_scores() -> None:
    assert reciprocal_rank_fusion_scores([]) == {}


def test_rrf_k_controls_how_quickly_rank_contribution_decays() -> None:
    small_k = reciprocal_rank_fusion_scores([["a", "b"]], rrf_k=1)
    large_k = reciprocal_rank_fusion_scores([["a", "b"]], rrf_k=1000)

    # With a small k, rank 1 dominates rank 2 much more sharply.
    small_k_ratio = small_k["a"] / small_k["b"]
    large_k_ratio = large_k["a"] / large_k["b"]
    assert small_k_ratio > large_k_ratio
