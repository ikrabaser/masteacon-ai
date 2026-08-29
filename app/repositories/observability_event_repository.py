"""Data-access layer for ObservabilityEvent."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observability_event import ObservabilityEvent


class ObservabilityEventRepository:
    """Encapsulates all database queries related to ObservabilityEvent rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        event_type: str,
        user_id: int,
        workspace_id: int | None,
        provider: str | None,
        model: str | None,
        success: bool,
        duration_ms: float,
        extra: dict,
    ) -> ObservabilityEvent:
        event = ObservabilityEvent(
            event_type=event_type,
            user_id=user_id,
            workspace_id=workspace_id,
            provider=provider,
            model=model,
            success=success,
            duration_ms=duration_ms,
            extra=extra,
        )
        self._session.add(event)
        await self._session.commit()
        return event

    async def list_by_user(self, user_id: int, since: datetime) -> list[ObservabilityEvent]:
        """Every event for a user since a given time — deliberately unaggregated;
        see app.services.observability_metrics for the (pure, easily-tested)
        aggregation logic this feeds.
        """
        result = await self._session.execute(
            select(ObservabilityEvent)
            .where(ObservabilityEvent.user_id == user_id, ObservabilityEvent.created_at >= since)
            .order_by(ObservabilityEvent.created_at.desc())
        )
        return list(result.scalars().all())
