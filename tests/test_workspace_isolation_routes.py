"""Route-level cross-user isolation tests.

This is the test the whole workspace feature exists for: User B must never be
able to read User A's workspaces or documents, at the HTTP layer, even when
User B knows (or guesses) User A's ids. All DB-touching dependencies are
overridden with in-memory fakes shared across requests in a test — no real
PostgreSQL connection is needed.
"""
import io

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_chunk_repository,
    get_document_repository,
    get_document_service,
    get_embedding_service,
    get_turnstile_service,
    get_user_repository,
    get_workspace_repository,
)
from app.core.config import get_settings
from app.main import app
from app.services.auth_service import AuthService
from app.services.chunking_service import ChunkingService
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.parsing_service import ParsingService
from tests.fakes import (
    FakeAuthProtectionService,
    FakeChunkRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeIndexingDispatcher,
    FakeTurnstileService,
    FakeUserRepository,
    FakeWorkspaceRepository,
)


@pytest.fixture
def client(tmp_path):
    users = FakeUserRepository()
    workspaces = FakeWorkspaceRepository()
    documents = FakeDocumentRepository()
    chunks = FakeChunkRepository()
    settings = get_settings()
    auth_protection = FakeAuthProtectionService()
    turnstile = FakeTurnstileService()

    indexing_service = DocumentIndexingService(
        document_repository=documents,
        chunk_repository=chunks,
        parsing_service=ParsingService(),
        chunking_service=ChunkingService(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap),
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        upload_directory=str(tmp_path),
    )
    document_service = DocumentService(
        document_repository=documents,
        chunk_repository=chunks,
        indexing_dispatcher=FakeIndexingDispatcher(indexing_service),
        upload_directory=str(tmp_path),
        max_upload_size_mb=settings.max_upload_size_mb,
    )

    app.dependency_overrides[get_auth_protection_service] = lambda: auth_protection
    app.dependency_overrides[get_turnstile_service] = lambda: turnstile
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_auth_service] = lambda: AuthService(users, settings)
    app.dependency_overrides[get_workspace_repository] = lambda: workspaces
    app.dependency_overrides[get_document_repository] = lambda: documents
    app.dependency_overrides[get_chunk_repository] = lambda: chunks
    app.dependency_overrides[get_embedding_service] = lambda: EmbeddingService(FakeEmbeddingProvider())
    app.dependency_overrides[get_document_service] = lambda: document_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _register(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_user_cannot_read_another_users_workspace(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")

    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a)
    ).json()

    response = client.get(f"/api/v1/workspaces/{workspace['id']}", headers=_auth_headers(token_b))

    assert response.status_code == 404


def test_user_does_not_see_another_users_workspace_in_list(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    client.post("/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a))

    response = client.get("/api/v1/workspaces", headers=_auth_headers(token_b))

    assert response.status_code == 200
    assert response.json() == []


def test_workspace_endpoints_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/workspaces")

    assert response.status_code == 401


def test_user_cannot_upload_into_another_users_workspace(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a)
    ).json()

    response = client.post(
        "/api/v1/documents",
        files={"file": ("doc.txt", io.BytesIO(b"hello world"), "text/plain")},
        data={"workspace_id": str(workspace["id"])},
        headers=_auth_headers(token_b),
    )

    assert response.status_code == 404


def test_user_cannot_list_documents_in_another_users_workspace(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a)
    ).json()
    client.post(
        "/api/v1/documents",
        files={"file": ("doc.txt", io.BytesIO(b"hello world, this is a real document."), "text/plain")},
        data={"workspace_id": str(workspace["id"])},
        headers=_auth_headers(token_a),
    )

    response = client.get(
        "/api/v1/documents", params={"workspace_id": workspace["id"]}, headers=_auth_headers(token_b)
    )

    assert response.status_code == 404


def test_user_cannot_get_a_document_from_another_users_workspace(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a)
    ).json()
    upload = client.post(
        "/api/v1/documents",
        files={"file": ("doc.txt", io.BytesIO(b"hello world, this is a real document."), "text/plain")},
        data={"workspace_id": str(workspace["id"])},
        headers=_auth_headers(token_a),
    ).json()

    response = client.get(
        f"/api/v1/documents/{upload['id']}",
        params={"workspace_id": workspace["id"]},
        headers=_auth_headers(token_b),
    )

    assert response.status_code == 404


def test_user_cannot_search_another_users_workspace(client: TestClient) -> None:
    token_a = _register(client, "alice@example.com")
    token_b = _register(client, "bob@example.com")
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token_a)
    ).json()

    response = client.post(
        "/api/v1/search",
        json={"workspace_id": workspace["id"], "query": "anything"},
        headers=_auth_headers(token_b),
    )

    assert response.status_code == 404


def test_owner_can_upload_list_and_fetch_their_own_document(client: TestClient) -> None:
    token = _register(client, "alice@example.com")
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "Alice's Workspace"}, headers=_auth_headers(token)
    ).json()

    upload = client.post(
        "/api/v1/documents",
        files={"file": ("doc.txt", io.BytesIO(b"hello world, this is a real document."), "text/plain")},
        data={"workspace_id": str(workspace["id"])},
        headers=_auth_headers(token),
    )
    assert upload.status_code == 201

    listing = client.get(
        "/api/v1/documents", params={"workspace_id": workspace["id"]}, headers=_auth_headers(token)
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    fetched = client.get(
        f"/api/v1/documents/{upload.json()['id']}",
        params={"workspace_id": workspace["id"]},
        headers=_auth_headers(token),
    )
    assert fetched.status_code == 200
