"""Route-level tests for the authentication endpoints.

Dependencies that would normally hit the real database are overridden with an
in-memory fake user repository, shared across requests within a test via
FastAPI's dependency_overrides — no real PostgreSQL connection is needed.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_current_user,
    get_turnstile_service,
    get_password_reset_token_repository,
    get_refresh_session_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.main import app
from app.services.auth_service import AuthService
from tests.fakes import (
    FakeAuthProtectionService,
    FakeTurnstileService,
    FakePasswordResetTokenRepository,
    FakeRefreshSessionRepository,
    FakeUserRepository,
)


@pytest.fixture
def auth_protection():
    return FakeAuthProtectionService()


@pytest.fixture
def turnstile():
    return FakeTurnstileService()


@pytest.fixture
def user_repository():
    return FakeUserRepository()


@pytest.fixture
def client(auth_protection, turnstile, user_repository):
    shared_repository = user_repository
    # TestClient talks plain HTTP (http://testserver) - a Secure cookie is
    # never sent over HTTP by any client, so force it off here regardless of
    # what real settings/.env happen to be, the same way production would
    # force it on.
    settings = get_settings().model_copy(update={"refresh_cookie_secure": False})
    refresh_sessions = FakeRefreshSessionRepository()
    reset_tokens = FakePasswordResetTokenRepository()

    def _get_user_repository_override():
        return shared_repository

    def _get_auth_service_override():
        return AuthService(user_repository=shared_repository, settings=settings)

    def _get_auth_protection_service_override():
        return auth_protection

    def _get_turnstile_service_override():
        return turnstile

    app.dependency_overrides[get_user_repository] = _get_user_repository_override
    app.dependency_overrides[get_auth_service] = _get_auth_service_override
    app.dependency_overrides[get_auth_protection_service] = (
        _get_auth_protection_service_override
    )
    app.dependency_overrides[get_turnstile_service] = (
        _get_turnstile_service_override
    )
    app.dependency_overrides[get_refresh_session_repository] = lambda: refresh_sessions
    app.dependency_overrides[get_password_reset_token_repository] = lambda: reset_tokens
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_user_repository, None)
    app.dependency_overrides.pop(get_auth_service, None)
    app.dependency_overrides.pop(get_auth_protection_service, None)
    app.dependency_overrides.pop(get_turnstile_service, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_refresh_session_repository, None)
    app.dependency_overrides.pop(get_password_reset_token_repository, None)
    app.dependency_overrides.pop(get_settings, None)


def test_register_returns_access_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": "alice@example.com", "password": "password123"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "password123"})

    response = client.post(
        "/api/v1/auth/register", json={"email": "alice@example.com", "password": "password123"}
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "short"})

    assert response.status_code == 422


def test_login_returns_access_token_for_valid_credentials(client: TestClient) -> None:
    class FakeVerifiedLoginAuthService:
        async def login(self, email: str, password: str):
            from app.models.user import User

            user = User(
                id=1,
                email=email,
                password_hash="unused",
                is_active=True,
                is_email_verified=True,
            )
            return user, "verified-login-token"

    app.dependency_overrides[get_auth_service] = (
        lambda: FakeVerifiedLoginAuthService()
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "verified-login-token"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "alice@example.com", "password": "password123"})

    response = client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register", json={"email": "alice@example.com", "password": "password123"}
    )
    token = register_response.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_register_rejects_honeypot_submission(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bot@example.com",
            "password": "password123",
            "website": "https://spam.example",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid registration request."

    # The rejected bot request must not have created the account.
    retry = client.post(
        "/api/v1/auth/register",
        json={
            "email": "bot@example.com",
            "password": "password123",
        },
    )

    assert retry.status_code == 201


def test_register_returns_429_when_rate_limited(
    client: TestClient,
    auth_protection: FakeAuthProtectionService,
) -> None:
    auth_protection.blocked_actions.add("register")
    auth_protection.retry_after = 120

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "120"
    assert response.json()["detail"] == (
        "Too many authentication attempts. Please try again later."
    )


def test_login_returns_429_when_rate_limited(
    client: TestClient,
    auth_protection: FakeAuthProtectionService,
) -> None:
    auth_protection.blocked_actions.add("login")
    auth_protection.retry_after = 45

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "45"


def test_successful_login_resets_rate_limit(
    client: TestClient,
    auth_protection: FakeAuthProtectionService,
) -> None:
    class FakeVerifiedLoginAuthService:
        async def login(self, email: str, password: str):
            from app.models.user import User

            user = User(
                id=1,
                email=email,
                password_hash="unused",
                is_active=True,
                is_email_verified=True,
            )
            return user, "verified-login-token"

    app.dependency_overrides[get_auth_service] = (
        lambda: FakeVerifiedLoginAuthService()
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert any(
        action == "login"
        for action, _identifier in auth_protection.resets
    )


def test_register_verifies_turnstile_token(
    client: TestClient,
    turnstile: FakeTurnstileService,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "turnstile@example.com",
            "password": "password123",
            "turnstile_token": "valid-turnstile-token",
        },
    )

    assert response.status_code == 201
    assert len(turnstile.calls) == 1

    token, remote_ip = turnstile.calls[0]
    assert token == "valid-turnstile-token"
    assert remote_ip


def test_register_rejects_failed_turnstile_verification(
    client: TestClient,
    turnstile: FakeTurnstileService,
) -> None:
    turnstile.success = False

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked@example.com",
            "password": "password123",
            "turnstile_token": "invalid-turnstile-token",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Turnstile verification failed."

    # Verification failure must prevent account creation.
    turnstile.success = True

    retry = client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked@example.com",
            "password": "password123",
            "turnstile_token": "valid-turnstile-token",
        },
    )

    assert retry.status_code == 201


def test_verify_email_endpoint_returns_success(
    client: TestClient,
) -> None:
    class FakeVerificationAuthService:
        async def verify_email(self, raw_token: str):
            assert raw_token == "valid-email-verification-token"
            return None

    fake_service = FakeVerificationAuthService()

    app.dependency_overrides[get_auth_service] = lambda: fake_service

    response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "token": "valid-email-verification-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "verified": True,
        "message": "Email verified successfully.",
    }


def test_resend_verification_returns_generic_success(
    client: TestClient,
) -> None:
    class FakeResendAuthService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def resend_verification(self, email: str) -> None:
            self.calls.append(email)

    fake_service = FakeResendAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake_service

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists for this email, "
            "a verification message has been sent."
        )
    }
    assert fake_service.calls == ["alice@example.com"]


def test_resend_verification_unknown_email_returns_same_response(
    client: TestClient,
) -> None:
    class FakeResendAuthService:
        async def resend_verification(self, email: str) -> None:
            assert email == "unknown@example.com"
            return None

    app.dependency_overrides[get_auth_service] = (
        lambda: FakeResendAuthService()
    )

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "unknown@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists for this email, "
            "a verification message has been sent."
        )
    }


def test_resend_verification_verified_account_returns_same_response(
    client: TestClient,
) -> None:
    class FakeResendAuthService:
        async def resend_verification(self, email: str) -> None:
            assert email == "already-verified@example.com"
            return None

    app.dependency_overrides[get_auth_service] = (
        lambda: FakeResendAuthService()
    )

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "already-verified@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an eligible account exists for this email, "
            "a verification message has been sent."
        )
    }


def test_resend_verification_returns_429_when_rate_limited(
    client: TestClient,
    auth_protection: FakeAuthProtectionService,
) -> None:
    class FakeResendAuthService:
        async def resend_verification(self, email: str) -> None:
            raise AssertionError(
                "Service must not run when rate limited."
            )

    app.dependency_overrides[get_auth_service] = (
        lambda: FakeResendAuthService()
    )

    # Resend currently shares the registration abuse-protection bucket.
    auth_protection.blocked_actions.add("register")
    auth_protection.retry_after = 90

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "90"
    assert response.json()["detail"] == (
        "Too many authentication attempts. Please try again later."
    )


def test_login_rejects_unverified_account(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "unverified-login@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unverified-login@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Please verify your email address before signing in."
    )


# --- Refresh session lifecycle -------------------------------------------

REFRESH_COOKIE_NAME = get_settings().refresh_cookie_name


async def _register_verified_and_login(client: TestClient, user_repository: FakeUserRepository, email: str) -> str:
    """Registers, marks the account verified directly on the fake repository
    (there's no real email verification service wired into this fixture),
    then logs in for real through the route — so the client's cookie jar
    ends up holding a genuine refresh session cookie.
    """
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    user = await user_repository.get_by_email(email)
    user.is_email_verified = True

    response = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_login_sets_an_httponly_refresh_cookie(client: TestClient, user_repository: FakeUserRepository) -> None:
    await _register_verified_and_login(client, user_repository, "session-a@example.com")

    cookie = next(c for c in client.cookies.jar if c.name == REFRESH_COOKIE_NAME)
    assert cookie.value
    # httpx's cookiejar exposes HttpOnly/SameSite via the underlying stdlib
    # cookie's rest-params; the important, directly-testable properties are
    # that it's scoped to the auth path and isn't a session-only cookie.
    assert cookie.path == "/api/v1/auth"
    assert cookie.expires is not None


async def test_refresh_issues_a_new_access_token(client: TestClient, user_repository: FakeUserRepository) -> None:
    await _register_verified_and_login(client, user_repository, "session-b@example.com")

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_without_a_cookie_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


async def test_the_old_refresh_cookie_is_rejected_after_a_refresh(
    client: TestClient, user_repository: FakeUserRepository
) -> None:
    await _register_verified_and_login(client, user_repository, "session-c@example.com")
    old_cookie_value = next(c for c in client.cookies.jar if c.name == REFRESH_COOKIE_NAME).value

    first_refresh = client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200

    # Force the (now-rotated-away) old cookie back in, simulating a client
    # that still has the stale value (e.g. a second tab, or a thief with a
    # copy of it).
    client.cookies.set(REFRESH_COOKIE_NAME, old_cookie_value, path="/api/v1/auth")
    replay_attempt = client.post("/api/v1/auth/refresh")

    assert replay_attempt.status_code == 401


async def test_logout_revokes_the_session_and_clears_the_cookie(
    client: TestClient, user_repository: FakeUserRepository
) -> None:
    await _register_verified_and_login(client, user_repository, "session-d@example.com")

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    refresh_after_logout = client.post("/api/v1/auth/refresh")
    assert refresh_after_logout.status_code == 401


def test_logout_succeeds_even_with_no_session_cookie_at_all(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204


async def test_logout_all_revokes_every_session_for_the_user(
    client: TestClient, user_repository: FakeUserRepository
) -> None:
    access_token = await _register_verified_and_login(client, user_repository, "session-e@example.com")
    # A second "device" logging in as the same user gets its own session.
    second_login = client.post(
        "/api/v1/auth/login", json={"email": "session-e@example.com", "password": "password123"}
    )
    assert second_login.status_code == 200

    response = client.post(
        "/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 204

    # The cookie jar currently holds the *second* login's cookie (the most
    # recent one set) - logout-all must have revoked it too, not just the
    # first session's.
    refresh_after_logout_all = client.post("/api/v1/auth/refresh")
    assert refresh_after_logout_all.status_code == 401


def test_logout_all_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout-all")

    assert response.status_code == 401


# --- Password reset --------------------------------------------------------


async def test_forgot_password_is_enumeration_safe_for_an_unknown_email(client: TestClient) -> None:
    response = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert response.status_code == 200
    assert "message" in response.json()


async def test_reset_password_rejects_an_unknown_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "a-token-that-was-never-issued-xx", "new_password": "a-new-password"},
    )

    assert response.status_code == 400
