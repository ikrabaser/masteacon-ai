"""Route-level tests for conversations: the RAG chat flow and cross-user isolation."""
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_chat_provider,
    get_chunk_repository,
    get_conversation_repository,
    get_embedding_service,
    get_message_repository,
    get_turnstile_service,
    get_refresh_session_repository,
    get_usage_guard_service,
    get_user_repository,
    get_workspace_repository,
)
from app.core.config import get_settings
from app.main import app
from app.services.auth_service import AuthService
from app.services.embedding_service import EmbeddingService
from tests.fakes import (
    FakeAuthProtectionService,
    FakeChatProvider,
    FakeChunkRepository,
    FakeChunkRow,
    FakeConversationRepository,
    FakeEmbeddingProvider,
    FakeMessageRepository,
    FakeTurnstileService,
    FakeRefreshSessionRepository,
    FakeUsageGuardService,
    FakeUserRepository,
    FakeWorkspaceRepository,
)


@pytest.fixture
def client():
    users = FakeUserRepository()
    workspaces = FakeWorkspaceRepository()
    conversations = FakeConversationRepository()
    messages = FakeMessageRepository()
    chunks = FakeChunkRepository(
        [FakeChunkRow(1, "doc.txt", 0, "Annual leave is 14 days.", 0.9, workspace_id=1)]
    )
    settings = get_settings()
    auth_protection = FakeAuthProtectionService()
    turnstile = FakeTurnstileService()

    app.dependency_overrides[get_auth_protection_service] = lambda: auth_protection
    app.dependency_overrides[get_turnstile_service] = lambda: turnstile
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_refresh_session_repository] = lambda: FakeRefreshSessionRepository()
    app.dependency_overrides[get_usage_guard_service] = lambda: FakeUsageGuardService()
    app.dependency_overrides[get_auth_service] = lambda: AuthService(users, settings)
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    app.dependency_overrides[get_conversation_repository] = lambda: conversations
    app.dependency_overrides[get_message_repository] = lambda: messages
    app.dependency_overrides[get_chunk_repository] = lambda: chunks
    app.dependency_overrides[get_embedding_service] = lambda: EmbeddingService(FakeEmbeddingProvider())
    app.dependency_overrides[get_chat_provider] = lambda: FakeChatProvider(
        answer="Annual leave is 14 days per year."
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _register(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_workspace(client: TestClient, token: str) -> dict:
    return client.post("/api/v1/workspaces", json={"name": "Workspace"}, headers=_auth_headers(token)).json()


def test_full_conversation_flow(client: TestClient) -> None:
    token = _register(client, "alice@example.com")
    workspace = _create_workspace(client, token)

    created = client.post(
        "/api/v1/conversations",
        json={"workspace_id": workspace["id"], "title": "Leave policy questions"},
        headers=_auth_headers(token),
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "How many days of annual leave do I get?"},
        headers=_auth_headers(token),
    )
    assert message.status_code == 201
    body = message.json()
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"
    assert len(body["sources"]) == 1

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=_auth_headers(token))
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2


def test_conversation_endpoints_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/conversations", params={"workspace_id": 1})

    assert response.status_code == 401


def test_user_cannot_read_another_users_conversation(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = _create_workspace(client, token_a)
    conversation = client.post(
        "/api/v1/conversations",
        json={"workspace_id": workspace["id"], "title": "Private"},
        headers=_auth_headers(token_a),
    ).json()

    response = client.get(f"/api/v1/conversations/{conversation['id']}", headers=_auth_headers(token_b))

    assert response.status_code == 404


def test_user_cannot_post_a_message_into_another_users_conversation(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = _create_workspace(client, token_a)
    conversation = client.post(
        "/api/v1/conversations",
        json={"workspace_id": workspace["id"], "title": "Private"},
        headers=_auth_headers(token_a),
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "Can I see this?"},
        headers=_auth_headers(token_b),
    )

    assert response.status_code == 404


def test_user_cannot_create_a_conversation_in_another_users_workspace(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = _create_workspace(client, token_a)

    response = client.post(
        "/api/v1/conversations",
        json={"workspace_id": workspace["id"], "title": "Sneaky"},
        headers=_auth_headers(token_b),
    )

    assert response.status_code == 404


def test_list_conversations_only_returns_the_current_users_conversations(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    workspace = _create_workspace(client, token_a)
    client.post(
        "/api/v1/conversations",
        json={"workspace_id": workspace["id"], "title": "Chat 1"},
        headers=_auth_headers(token_a),
    )

    response = client.get(
        "/api/v1/conversations", params={"workspace_id": workspace["id"]}, headers=_auth_headers(token_a)
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# --- /api/v1/ask usage guardrails -------------------------------------------


def test_ask_is_throttled_when_the_per_user_usage_guard_denies_it(client: TestClient) -> None:
    token = _register(client, "throttled-ask@example.com")
    workspace = _create_workspace(client, token)
    app.dependency_overrides[get_usage_guard_service] = lambda: FakeUsageGuardService(allow=False)

    response = client.post(
        "/api/v1/ask",
        json={"question": "How many days of annual leave do I get?", "workspace_id": workspace["id"]},
        headers=_auth_headers(token),
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_ask_still_enforces_workspace_ownership_before_any_llm_call(client: TestClient) -> None:
    token_a = _register(client, "owner@example.com")
    token_b = _register(client, "intruder@example.com")
    workspace = _create_workspace(client, token_a)

    response = client.post(
        "/api/v1/ask",
        json={"question": "Anything in here?", "workspace_id": workspace["id"]},
        headers=_auth_headers(token_b),
    )

    assert response.status_code == 404
