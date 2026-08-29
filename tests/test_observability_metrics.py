"""Tests for the pure observability aggregation logic — no DB, no fakes needed."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.services.observability_metrics import summarize_events


@dataclass
class _Event:
    event_type: str
    created_at: datetime
    success: bool
    duration_ms: float
    extra: dict = field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_summarize_events_handles_an_empty_list() -> None:
    summary = summarize_events([], days=7)

    assert summary.total_requests == 0
    assert summary.success_rate == 0.0
    assert summary.avg_duration_ms == 0.0
    assert summary.events_by_type == {}
    assert len(summary.daily_counts) == 7
    assert all(day.count == 0 for day in summary.daily_counts)
    assert summary.top_tools == []


def test_summarize_events_computes_success_rate_and_avg_duration() -> None:
    events = [
        _Event("rag_request", _now(), True, 100.0),
        _Event("rag_request", _now(), True, 200.0),
        _Event("rag_request", _now(), False, 300.0),
    ]

    summary = summarize_events(events, days=1)

    assert summary.total_requests == 3
    assert summary.success_rate == round(2 / 3, 4)
    assert summary.avg_duration_ms == 200.0


def test_summarize_events_counts_by_event_type() -> None:
    events = [
        _Event("rag_request", _now(), True, 10.0),
        _Event("agent_request", _now(), True, 10.0),
        _Event("agent_request", _now(), True, 10.0),
        _Event("tool_call", _now(), True, 10.0),
    ]

    summary = summarize_events(events, days=1)

    assert summary.events_by_type == {"rag_request": 1, "agent_request": 2, "tool_call": 1}


def test_summarize_events_zero_fills_days_with_no_activity() -> None:
    today = _now()
    events = [_Event("rag_request", today, True, 10.0)]

    summary = summarize_events(events, days=3)

    assert len(summary.daily_counts) == 3
    # Today's bucket (last one, chronological order) got the one event.
    assert summary.daily_counts[-1].count == 1
    assert summary.daily_counts[0].count == 0
    assert summary.daily_counts[1].count == 0


def test_summarize_events_ignores_events_outside_the_window() -> None:
    old_event = _Event("rag_request", _now() - timedelta(days=30), True, 10.0)
    recent_event = _Event("rag_request", _now(), True, 20.0)

    summary = summarize_events([old_event, recent_event], days=3)

    # summarize_events doesn't filter by window itself (the repository does,
    # via `since`) - but its day-bucketing must not crash or silently include
    # an out-of-window day in daily_counts.
    assert sum(day.count for day in summary.daily_counts) == 1
    assert summary.total_requests == 2  # totals/averages are still over everything passed in


def test_summarize_events_counts_top_tools_from_tool_call_events_only() -> None:
    events = [
        _Event("tool_call", _now(), True, 10.0, extra={"tool_name": "search_knowledge"}),
        _Event("tool_call", _now(), True, 10.0, extra={"tool_name": "search_knowledge"}),
        _Event("tool_call", _now(), True, 10.0, extra={"tool_name": "workspace_stats"}),
        # An agent_request also lists tool_names, but must not be double-counted.
        _Event("agent_request", _now(), True, 10.0, extra={"tool_names": ["search_knowledge", "workspace_stats"]}),
    ]

    summary = summarize_events(events, days=1)

    tools = {t.tool_name: t.count for t in summary.top_tools}
    assert tools == {"search_knowledge": 2, "workspace_stats": 1}
