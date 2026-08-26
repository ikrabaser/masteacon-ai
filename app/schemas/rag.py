"""Pydantic schemas for the RAG question-answering endpoint."""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request body for POST /api/v1/ask."""

    workspace_id: int
    question: str = Field(min_length=1, max_length=2000)


class SourceItem(BaseModel):
    """A retrieved chunk offered to the model as context for the answer."""

    document_id: int
    filename: str
    chunk_index: int
    similarity_score: float
    content: str
    # 1-based — matches the "[N]" marker the model is instructed to cite this
    # source with inline in `AskResponse.answer` (e.g. "...supports it [1].").
    citation_marker: int
    # Whether the model's answer actually contains a "[citation_marker]"
    # reference to this source — a chunk can be retrieved as context without
    # ever actually being cited in the final answer.
    cited: bool


class AskResponse(BaseModel):
    """Response body for POST /api/v1/ask."""

    answer: str
    sources: list[SourceItem]
    # None when the groundedness check wasn't run (disabled via config);
    # True/False when it was — see GROUNDEDNESS_CHECK_ENABLED.
    grounded: bool | None = None
