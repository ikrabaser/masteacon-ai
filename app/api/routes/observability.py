"""Observability dashboard endpoint — always scoped to the calling user's own events.

There is no admin/cross-user view: this is a personal knowledge assistant, not
a multi-tenant admin console, so "observability" here means letting a user see
their own request history and reliability, never anyone else's.
"""
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user, get_observability_service
from app.models.user import User
from app.schemas.observability import DailyCountItem, ObservabilitySummaryResponse, ToolUsageItem
from app.services.observability_service import ObservabilityService

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@router.get("/summary", response_model=ObservabilitySummaryResponse)
async def get_observability_summary(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ObservabilitySummaryResponse:
    """Aggregate stats over the caller's own rag_request/agent_request/tool_call events."""
    summary = await observability_service.get_summary(current_user.id, days=days)
    return ObservabilitySummaryResponse(
        days=days,
        total_requests=summary.total_requests,
        success_rate=summary.success_rate,
        avg_duration_ms=summary.avg_duration_ms,
        events_by_type=summary.events_by_type,
        daily_counts=[DailyCountItem(date=d.date, count=d.count) for d in summary.daily_counts],
        top_tools=[ToolUsageItem(tool_name=t.tool_name, count=t.count) for t in summary.top_tools],
    )
