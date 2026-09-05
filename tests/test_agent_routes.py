"""Route-level tests for the agent endpoint: auth, tool execution, cross-user isolation."""
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_chat_provider,
    get_chunk_repository,
    get_document_repository,
    get_embedding_service,
    get_turnstile_service,
    get_refresh_session_repository,
    get_user_repository,
    get_workspace_repository,
)
from app.core.config import get_settings
from app.main import app
from app.providers.base_chat_provider import RequestedToolCall, ToolCallDecision
from app.services.auth_service import AuthService
from app.services.embedding_service import EmbeddingService
from tests.fakes import (
    FakeAuthProtectionService,
    FakeChatProvider,
    FakeChunkRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeTurnstileService,
    FakeRefreshSessionRepository,
    FakeUserRepository,
    FakeWorkspaceRepository,
)


@pytest.fixture
def client():
    users = FakeUserRepository()
    workspaces = FakeWorkspaceRepository()
    documents = FakeDocumentRepository()
    chunks = FakeChunkRepository()
    settings = get_settings()
    auth_protection = FakeAuthProtectionService()
    turnstile = FakeTurnstileService()

    app.dependency_overrides[get_auth_protection_service] = lambda: auth_protection
    app.dependency_overrides[get_turnstile_service] = lambda: turnstile
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_refresh_session_repository] = lambda: FakeRefreshSessionRepository()
    app.dependency_overrides[get_auth_service] = lambda: AuthService(users, settings)
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    app.dependency_overrides[get_document_repository] = lambda: documents
    app.dependency_overrides[get_chunk_repository] = lambda: chunks
    app.dependency_overrides[get_embedding_service] = lambda: EmbeddingService(FakeEmbeddingProvider())

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _register(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_agent_ask_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/agent/ask", json={"question": "What are my workspaces?"})

    assert response.status_code == 401


def test_agent_ask_answers_directly_without_tools(client: TestClient) -> None:
    token = _register(client, "alice@example.com")
    app.dependency_overrides[get_chat_provider] = lambda: FakeChatProvider(
        tool_decision=ToolCallDecision(text="Hello!", tool_calls=[])
    )

    response = client.post(
        "/api/v1/agent/ask", json={"question": "Say hello"}, headers=_auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Hello!"
    assert response.json()["tool_calls"] == []


def test_agent_ask_uses_a_tool_and_only_sees_the_callers_own_workspaces(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    client.post("/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a))
    client.post("/api/v1/workspaces", json={"name": "Bob's Workspace"}, headers=_auth_headers(token_b))

    app.dependency_overrides[get_chat_provider] = lambda: FakeChatProvider(
        answer="You have one workspace.",
        tool_decision=ToolCallDecision(
            text=None, tool_calls=[RequestedToolCall(id="call-1", name="list_workspaces", arguments={})]
        ),
    )

    response = client.post(
        "/api/v1/agent/ask", json={"question": "What workspaces do I have?"}, headers=_auth_headers(token_a)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool_calls"][0]["success"] is True
    workspace_names = [w["name"] for w in body["tool_calls"][0]["result"]["workspaces"]]
    assert workspace_names == ["Alice's Workspace"]
