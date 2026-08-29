"""Pydantic schemas for the observability dashboard endpoint."""
from pydantic import BaseModel


class DailyCountItem(BaseModel):
    date: str
    count: int


class ToolUsageItem(BaseModel):
    tool_name: str
    count: int


class ObservabilitySummaryResponse(BaseModel):
    """Response body for GET /api/v1/observability/summary."""

    days: int
    total_requests: int
    success_rate: float
    avg_duration_ms: float
    events_by_type: dict[str, int]
    daily_counts: list[DailyCountItem]
    top_tools: list[ToolUsageItem]
