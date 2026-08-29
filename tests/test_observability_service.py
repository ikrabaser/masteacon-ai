"""Tests for ObservabilityService: recording (best-effort) and summarizing."""
from datetime import datetime, timezone

import pytest

from app.services.observability_service import ObservabilityService


class _FakeObservabilityEventRepository:
    def __init__(self, raise_on_create: Exception | None = None) -> None:
        self.created: list[dict] = []
        self._raise_on_create = raise_on_create

    async def create(self, **kwargs):
        if self._raise_on_create is not None:
            raise self._raise_on_create
        self.created.append(kwargs)

    async def list_by_user(self, user_id: int, since):
        class _Row:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        return [
            _Row(
                event_type="rag_request",
                created_at=datetime.now(timezone.utc),
                success=True,
                duration_ms=123.0,
                extra={},
            )
        ]


@pytest.mark.asyncio
async def test_record_event_writes_to_the_repository() -> None:
    repository = _FakeObservabilityEventRepository()
    service = ObservabilityService(repository)

    await service.record_event(
        event_type="rag_request", user_id=1, success=True, duration_ms=42.0, workspace_id=3, extra={"foo": "bar"}
    )

    assert len(repository.created) == 1
    assert repository.created[0]["event_type"] == "rag_request"
    assert repository.created[0]["extra"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_record_event_swallows_a_repository_failure() -> None:
    repository = _FakeObservabilityEventRepository(raise_on_create=RuntimeError("db is down"))
    service = ObservabilityService(repository)

    # Must not raise - a broken observability write must never break the
    # actual RAG/agent/tool response.
    await service.record_event(event_type="rag_request", user_id=1, success=True, duration_ms=1.0)


@pytest.mark.asyncio
async def test_get_summary_delegates_to_the_pure_aggregation_function() -> None:
    repository = _FakeObservabilityEventRepository()
    service = ObservabilityService(repository)

    summary = await service.get_summary(user_id=1, days=7)

    assert summary.total_requests == 1
    assert summary.success_rate == 1.0
