"""Records structured application events for the observability dashboard, and
summarizes them into dashboard-ready aggregates.

Recording is always best-effort: RagService/AgentService/ToolExecutionService
call `record_event()` right after they emit their existing structured JSON
log line (see app/core/logging.py) with the exact same field values — this
table exists purely so that data has a queryable history instead of only an
ephemeral stdout log line. A failure to write here is logged and swallowed,
never allowed to affect the actual RAG/agent/tool response.
"""
from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.repositories.observability_event_repository import ObservabilityEventRepository
from app.services.observability_metrics import ObservabilitySummary, summarize_events

logger = get_logger(__name__)


class ObservabilityService:
    """Records and summarizes rag_request/agent_request/tool_call events."""

    def __init__(self, repository: ObservabilityEventRepository) -> None:
        self._repository = repository

    async def record_event(
        self,
        *,
        event_type: str,
        user_id: int,
        success: bool,
        duration_ms: float,
        workspace_id: int | None = None,
        provider: str | None = None,
        model: str | None = None,
        extra: dict | None = None,
    ) -> None:
        try:
            await self._repository.create(
                event_type=event_type,
                user_id=user_id,
                workspace_id=workspace_id,
                provider=provider,
                model=model,
                success=success,
                duration_ms=duration_ms,
                extra=extra or {},
            )
        except Exception:
            logger.exception("Failed to persist an observability event (event_type=%s)", event_type)

    async def get_summary(self, user_id: int, days: int = 7) -> ObservabilitySummary:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        events = await self._repository.list_by_user(user_id, since=since)
        return summarize_events(events, days=days)
