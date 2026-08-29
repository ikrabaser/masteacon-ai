"""Route-level tests for the observability dashboard endpoint."""
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_observability_event_repository,
    get_turnstile_service,
    get_user_repository,
)
from app.core.config import get_settings
from app.main import app
from app.services.auth_service import AuthService
from tests.fakes import (
    FakeAuthProtectionService,
    FakeObservabilityEventRepository,
    FakeTurnstileService,
    FakeUserRepository,
)


@pytest.fixture
def client():
    users = FakeUserRepository()
    settings = get_settings()
    observability_events = FakeObservabilityEventRepository()

    app.dependency_overrides[get_auth_protection_service] = lambda: FakeAuthProtectionService()
    app.dependency_overrides[get_turnstile_service] = lambda: FakeTurnstileService()
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_auth_service] = lambda: AuthService(users, settings)
    app.dependency_overrides[get_observability_event_repository] = lambda: observability_events

    with TestClient(app) as test_client:
        test_client.observability_events = observability_events  # type: ignore[attr-defined]
        yield test_client

    app.dependency_overrides.clear()


def _register(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_observability_summary_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/observability/summary")

    assert response.status_code == 401


def test_observability_summary_returns_zeroed_report_with_no_events(client: TestClient) -> None:
    token = _register(client, "alice@example.com")

    response = client.get("/api/v1/observability/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 0
    assert body["success_rate"] == 0.0
    assert len(body["daily_counts"]) == 7  # default `days`


def test_observability_summary_only_reports_the_callers_own_events(client: TestClient) -> None:
    alice_token = _register(client, "alice@example.com")
    _register(client, "bob@example.com")

    alice_id = 1  # first registered user
    bob_id = 2

    import asyncio

    async def _seed():
        await client.observability_events.create(  # type: ignore[attr-defined]
            event_type="rag_request", user_id=alice_id, workspace_id=1, provider=None, model=None,
            success=True, duration_ms=10.0, extra={},
        )
        await client.observability_events.create(  # type: ignore[attr-defined]
            event_type="rag_request", user_id=bob_id, workspace_id=1, provider=None, model=None,
            success=True, duration_ms=10.0, extra={},
        )

    asyncio.run(_seed())

    response = client.get("/api/v1/observability/summary", headers={"Authorization": f"Bearer {alice_token}"})

    assert response.status_code == 200
    assert response.json()["total_requests"] == 1
