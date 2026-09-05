"""Tests for the liveness/readiness endpoints and the root endpoint."""
from fastapi.testclient import TestClient

from app.api.dependencies import get_redis_client
from app.core.database import get_db
from app.main import app


def test_health_alias_returns_alive() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_liveness_returns_alive_without_checking_any_dependency() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


class _FakeSession:
    def __init__(self, raise_error: bool = False) -> None:
        self._raise_error = raise_error

    async def execute(self, _statement):
        if self._raise_error:
            raise ConnectionError("could not connect to server")


class _FakeRedis:
    def __init__(self, raise_error: bool = False) -> None:
        self._raise_error = raise_error

    async def ping(self):
        if self._raise_error:
            raise ConnectionError("connection refused")
        return True


async def _fake_db_ok():
    yield _FakeSession()


async def _fake_db_down():
    yield _FakeSession(raise_error=True)


def test_readiness_returns_200_when_all_dependencies_are_up() -> None:
    app.dependency_overrides[get_db] = _fake_db_ok
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedis()

    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"database": "ok", "redis": "ok"}


def test_readiness_returns_503_when_database_is_down() -> None:
    app.dependency_overrides[get_db] = _fake_db_down
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedis()

    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "unreachable"
    assert body["checks"]["redis"] == "ok"


def test_readiness_returns_503_when_redis_is_down() -> None:
    app.dependency_overrides[get_db] = _fake_db_ok
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedis(raise_error=True)

    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "unreachable"


def test_readiness_never_leaks_exception_detail_in_the_response() -> None:
    app.dependency_overrides[get_db] = _fake_db_down
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedis()

    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert "could not connect to server" not in response.text


def test_root_returns_app_info() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert body["docs"] == "/docs"
