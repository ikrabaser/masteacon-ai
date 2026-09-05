"""Unit tests for RefreshSessionService: issuance, rotation, replay detection, revocation."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import InvalidRefreshTokenError
from app.core.secure_token import hash_token
from app.services.refresh_session_service import RefreshSessionService
from tests.fakes import FakeRefreshSessionRepository

USER_ID = 1


def _service(repository: FakeRefreshSessionRepository | None = None) -> RefreshSessionService:
    return RefreshSessionService(repository or FakeRefreshSessionRepository(), ttl_days=30)


@pytest.mark.asyncio
async def test_issue_returns_a_usable_raw_token() -> None:
    service = _service()

    session = await service.issue(USER_ID)

    assert session.raw_token
    assert session.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_rotate_returns_the_user_id_and_a_new_token() -> None:
    service = _service()
    issued = await service.issue(USER_ID)

    user_id, rotated = await service.rotate(issued.raw_token)

    assert user_id == USER_ID
    assert rotated.raw_token != issued.raw_token


@pytest.mark.asyncio
async def test_the_old_token_is_rejected_after_rotation() -> None:
    service = _service()
    issued = await service.issue(USER_ID)
    await service.rotate(issued.raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(issued.raw_token)


@pytest.mark.asyncio
async def test_replaying_a_rotated_token_revokes_every_session_for_the_user() -> None:
    repository = FakeRefreshSessionRepository()
    service = _service(repository)
    issued = await service.issue(USER_ID)
    _, rotated = await service.rotate(issued.raw_token)

    # The attacker replays the now-revoked original token...
    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(issued.raw_token)

    # ...which must also revoke the legitimate, freshly-rotated session -
    # the whole point of replay detection is to lock the account down.
    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(rotated.raw_token)


@pytest.mark.asyncio
async def test_an_unknown_token_is_rejected() -> None:
    service = _service()

    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate("this-was-never-issued")


@pytest.mark.asyncio
async def test_an_expired_token_is_rejected() -> None:
    repository = FakeRefreshSessionRepository()
    service = _service(repository)
    issued = await service.issue(USER_ID)
    # Force it into the past.
    session = await repository.get_by_token_hash(hash_token(issued.raw_token))
    session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(issued.raw_token)


@pytest.mark.asyncio
async def test_revoke_disables_exactly_the_presented_session() -> None:
    service = _service()
    session_a = await service.issue(USER_ID)
    session_b = await service.issue(USER_ID)

    await service.revoke(session_a.raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(session_a.raw_token)
    # session_b is untouched.
    await service.rotate(session_b.raw_token)


@pytest.mark.asyncio
async def test_revoke_is_a_no_op_for_an_unknown_token() -> None:
    service = _service()

    await service.revoke("never-issued")  # must not raise


@pytest.mark.asyncio
async def test_revoke_all_for_user_disables_every_active_session() -> None:
    service = _service()
    session_a = await service.issue(USER_ID)
    session_b = await service.issue(USER_ID)

    await service.revoke_all_for_user(USER_ID)

    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(session_a.raw_token)
    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(session_b.raw_token)


@pytest.mark.asyncio
async def test_revoke_all_for_user_never_touches_another_users_sessions() -> None:
    service = _service()
    mine = await service.issue(USER_ID)
    someone_elses = await service.issue(USER_ID + 1)

    await service.revoke_all_for_user(USER_ID)

    with pytest.raises(InvalidRefreshTokenError):
        await service.rotate(mine.raw_token)
    # Someone else's session is untouched.
    await service.rotate(someone_elses.raw_token)
