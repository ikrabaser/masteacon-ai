"""Pure aggregation logic for the observability dashboard.

No DB, no I/O — this only ever operates on a plain list of already-fetched
events, so it's fully unit-testable without a repository or database.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class ObservabilityEventLike(Protocol):
    """The shape summarize_events() needs — structurally satisfied by the
    ObservabilityEvent ORM model, without importing it (keeps this module
    dependency-free)."""

    event_type: str
    created_at: datetime
    success: bool
    duration_ms: float
    extra: dict


@dataclass(frozen=True)
class DailyCount:
    """Event count for one calendar day (UTC)."""

    date: str  # ISO date, e.g. "2026-08-27"
    count: int


@dataclass(frozen=True)
class ToolUsage:
    """How many times one tool was called."""

    tool_name: str
    count: int


@dataclass(frozen=True)
class ObservabilitySummary:
    """Dashboard-ready aggregates over a window of events."""

    total_requests: int
    success_rate: float  # 0..1, 0.0 when there are no events
    avg_duration_ms: float
    events_by_type: dict[str, int]
    daily_counts: list[DailyCount]  # every day in the window, in order, zero-filled
    top_tools: list[ToolUsage]  # most-called tools first


def summarize_events(events: list[ObservabilityEventLike], days: int) -> ObservabilitySummary:
    """Aggregate a list of events (any order) into an ObservabilitySummary
    covering exactly `days` calendar days ending today (UTC), zero-filled for
    days with no activity so a chart never has to guess at missing dates.
    """
    total = len(events)
    successes = sum(1 for event in events if event.success)
    avg_duration_ms = sum(event.duration_ms for event in events) / total if total else 0.0
    events_by_type = dict(Counter(event.event_type for event in events))

    today = datetime.now(timezone.utc).date()
    buckets = {(today - timedelta(days=offset)).isoformat(): 0 for offset in range(days - 1, -1, -1)}
    for event in events:
        day = event.created_at.date().isoformat()
        if day in buckets:
            buckets[day] += 1
    daily_counts = [DailyCount(date=day, count=count) for day, count in buckets.items()]

    # Only "tool_call" events carry a single tool_name — counting from
    # "agent_request"'s tool_names list too would double-count the same call.
    tool_counter: Counter[str] = Counter()
    for event in events:
        if event.event_type == "tool_call":
            tool_name = (event.extra or {}).get("tool_name")
            if tool_name:
                tool_counter[tool_name] += 1
    top_tools = [ToolUsage(tool_name=name, count=count) for name, count in tool_counter.most_common(10)]

    return ObservabilitySummary(
        total_requests=total,
        success_rate=round(successes / total, 4) if total else 0.0,
        avg_duration_ms=round(avg_duration_ms, 2),
        events_by_type=events_by_type,
        daily_counts=daily_counts,
        top_tools=top_tools,
    )
