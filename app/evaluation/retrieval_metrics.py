"""Mechanical retrieval-quality metrics — no LLM involved, fully deterministic
given a fixed corpus and a fixed set of "relevant" document ids per question.

Standard information-retrieval metrics (see e.g. RAGAS's retrieval-hit-rate /
MRR / recall@k definitions), reimplemented directly here as small pure
functions so they're trivially unit tested and carry no framework dependency.
"""


def hit(retrieved_document_ids: list[int], relevant_document_ids: set[int]) -> bool:
    """Whether *any* relevant document was retrieved at all."""
    return any(doc_id in relevant_document_ids for doc_id in retrieved_document_ids)


def reciprocal_rank(retrieved_document_ids: list[int], relevant_document_ids: set[int]) -> float:
    """1 / (rank of the first relevant document), 0 if none was retrieved.

    Rank is 1-based — a relevant document retrieved first scores 1.0, second
    scores 0.5, and so on. This is the per-case term Mean Reciprocal Rank
    (MRR) averages across a whole evaluation set.
    """
    for rank, doc_id in enumerate(retrieved_document_ids, start=1):
        if doc_id in relevant_document_ids:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_document_ids: list[int], relevant_document_ids: set[int]) -> float:
    """Fraction of all relevant documents that appear anywhere in the retrieved set."""
    if not relevant_document_ids:
        return 0.0
    retrieved_set = set(retrieved_document_ids)
    return len(retrieved_set & relevant_document_ids) / len(relevant_document_ids)


def precision_at_k(retrieved_document_ids: list[int], relevant_document_ids: set[int]) -> float:
    """Fraction of the retrieved documents that were actually relevant."""
    if not retrieved_document_ids:
        return 0.0
    relevant_retrieved = sum(1 for doc_id in retrieved_document_ids if doc_id in relevant_document_ids)
    return relevant_retrieved / len(retrieved_document_ids)
