"""ObservabilityEvent ORM model.

One row per structured event already emitted to the JSON application log
(`rag_request` / `agent_request` / `tool_call` — see app/core/logging.py), so
the observability dashboard has a queryable history instead of only an
ephemeral stdout log line. Recording is always best-effort: a failure to
write this table must never affect the actual RAG/agent/tool response — see
ObservabilityService.record_event.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ObservabilityEvent(Base):
    """A single recorded rag_request/agent_request/tool_call event."""

    __tablename__ = "observability_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    # Event-specific detail (retrieved_chunk_count, tool_name, tool_call_count,
    # grounded, stop_reason, ...) — the same shape already sent to the
    # structured JSON logger's `extra={}`, kept flexible rather than adding a
    # nullable column per event type.
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
