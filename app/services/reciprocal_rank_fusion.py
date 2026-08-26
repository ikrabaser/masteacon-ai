"""Reciprocal Rank Fusion (RRF) — combines multiple independently-ranked result
lists into one fused ranking, without needing the lists' scores to be on the
same scale (which vector cosine-similarity and PostgreSQL's `ts_rank` are not).

Kept as a small, pure, dependency-free function so it can be unit tested on its
own, separately from the database query that produces each ranked list.
"""
from typing import Hashable


def reciprocal_rank_fusion_scores(
    ranked_key_lists: list[list[Hashable]],
    rrf_k: int = 60,
) -> dict[Hashable, float]:
    """Return `{item_key: fused_score}` for items ranked (1-based) across one or
    more lists.

    Each item's fused score is the sum of `1 / (rrf_k + rank)` across every list
    it appears in — an item ranked highly in *any* list scores well, and one
    ranked well in *multiple* lists scores higher than it would from either
    list alone. Higher is better; sort the result descending by value to get
    the fused ranking. `rrf_k=60` is the standard default from the original RRF
    paper (Cormack et al., 2009) — the fusion's *relative* ordering is not
    sensitive to small changes in it, it only controls how quickly a rank's
    contribution decays.
    """
    scores: dict[Hashable, float] = {}
    for ranked_keys in ranked_key_lists:
        for rank, item_key in enumerate(ranked_keys, start=1):
            scores[item_key] = scores.get(item_key, 0.0) + 1.0 / (rrf_k + rank)
    return scores
