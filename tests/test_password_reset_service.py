"""Unit tests for PasswordResetService."""
import pytest

from app.core.exceptions import InvalidRefreshTokenError, PasswordResetError
from app.core.secure_token import hash_token
from app.core.security import verify_password
from app.services.password_reset_service import PasswordResetService
from app.services.refresh_session_service import RefreshSessionService
from tests.fakes import FakePasswordResetTokenRepository, FakeRefreshSessionRepository, FakeUserRepository


class _RecordingEmailService:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_password_reset_email(self, *, to_email: str, raw_token: str) -> bool:
        self.sent.append((to_email, raw_token))
        return True


def _build():
    users = FakeUserRepository()
    refresh_repository = FakeRefreshSessionRepository()
    refresh_sessions = RefreshSessionService(refresh_repository, ttl_days=30)
    reset_tokens = FakePasswordResetTokenRepository()
    email_service = _RecordingEmailService()
    service = PasswordResetService(
        user_repository=users,
        reset_token_repository=reset_tokens,
        refresh_session_service=refresh_sessions,
        email_service=email_service,
        ttl_minutes=30,
    )
    return service, users, refresh_sessions, email_service, reset_tokens


@pytest.mark.asyncio
async def test_forgot_password_sends_nothing_for_an_unknown_email() -> None:
    service, _, _, email_service, _ = _build()

    await service.forgot_password("nobody@example.com")

    assert email_service.sent == []


@pytest.mark.asyncio
async def test_forgot_password_emails_a_reset_link_for_a_real_user() -> None:
    service, users, _, email_service, reset_tokens = _build()
    user = await users.create(email="alice@example.com", password_hash="irrelevant-hash")

    await service.forgot_password("alice@example.com")

    assert len(email_service.sent) == 1
    assert email_service.sent[0][0] == "alice@example.com"
    raw_token = email_service.sent[0][1]
    stored = await reset_tokens.get_by_token_hash(hash_token(raw_token))
    assert stored is not None
    assert stored.user_id == user.id


@pytest.mark.asyncio
async def test_forgot_password_sends_nothing_for_an_inactive_user() -> None:
    service, users, _, email_service, _ = _build()
    user = await users.create(email="alice@example.com", password_hash="hash")
    user.is_active = False

    await service.forgot_password("alice@example.com")

    assert email_service.sent == []


@pytest.mark.asyncio
async def test_reset_password_sets_a_new_password_and_revokes_all_sessions() -> None:
    service, users, refresh_sessions, email_service, _ = _build()
    user = await users.create(email="alice@example.com", password_hash="old-hash")
    session = await refresh_sessions.issue(user.id)

    await service.forgot_password("alice@example.com")
    raw_reset_token = email_service.sent[0][1]

    await service.reset_password(raw_reset_token, "a-brand-new-password")

    assert verify_password("a-brand-new-password", user.password_hash)
    with pytest.raises(InvalidRefreshTokenError):
        await refresh_sessions.rotate(session.raw_token)


@pytest.mark.asyncio
async def test_reset_token_cannot_be_used_twice() -> None:
    service, users, _, email_service, _ = _build()
    await users.create(email="alice@example.com", password_hash="old-hash")
    await service.forgot_password("alice@example.com")
    raw_reset_token = email_service.sent[0][1]

    await service.reset_password(raw_reset_token, "first-new-password")

    with pytest.raises(PasswordResetError):
        await service.reset_password(raw_reset_token, "second-new-password")


@pytest.mark.asyncio
async def test_an_unknown_reset_token_is_rejected() -> None:
    service, _, _, _, _ = _build()

    with pytest.raises(PasswordResetError):
        await service.reset_password("never-issued", "a-new-password")


@pytest.mark.asyncio
async def test_an_expired_reset_token_is_rejected() -> None:
    service, users, _, email_service, reset_tokens = _build()
    await users.create(email="alice@example.com", password_hash="old-hash")
    await service.forgot_password("alice@example.com")
    raw_reset_token = email_service.sent[0][1]

    stored = await reset_tokens.get_by_token_hash(hash_token(raw_reset_token))
    from datetime import datetime, timedelta, timezone

    stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    with pytest.raises(PasswordResetError):
        await service.reset_password(raw_reset_token, "a-new-password")
