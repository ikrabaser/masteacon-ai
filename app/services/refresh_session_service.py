"""Server-side refresh session issuance, rotation, and revocation.

Question -> Log in -> issue (access token, refresh session) -> ... -> refresh
rotates the session -> ... -> logout/logout-all/password-reset revokes it.

The raw refresh token is generated here and handed back to the caller (the
route layer sets it as an HttpOnly cookie) exactly once, at issuance time —
only its SHA-256 hash is ever persisted (RefreshSession.token_hash), so a
database leak alone can never be turned into a working session.

Rotation: every successful refresh revokes the presented session and issues
a brand-new one in its place (`replaced_by_id` links them). Replay
protection: presenting a token that was revoked *by rotation* — i.e. a
legitimate client has already moved on to the new one — means someone else
has a copy of the old token, so every session for that user is revoked and
the caller must log in again. This is deliberately aggressive: a false
positive (e.g. two tabs racing to refresh) costs the user one extra login;
letting a real replay through costs their whole account. A token revoked by
logout/logout-all/password-reset instead is just rejected on its own — reuse
there means a stale client, not evidence of compromise, and must not log the
user's other, still-legitimate sessions out.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.exceptions import InvalidRefreshTokenError
from app.core.logging import get_logger
from app.core.secure_token import current_time, generate_secure_token, hash_token, is_expired
from app.repositories.refresh_session_repository import RefreshSessionRepository

logger = get_logger(__name__)


@dataclass(frozen=True)
class IssuedSession:
    raw_token: str
    expires_at: datetime


class RefreshSessionService:
    """Issues, rotates, and revokes server-side refresh sessions."""

    def __init__(self, repository: RefreshSessionRepository, ttl_days: int) -> None:
        self._repository = repository
        self._ttl_days = ttl_days

    async def issue(self, user_id: int) -> IssuedSession:
        """Create a brand-new refresh session (login/register)."""
        token = generate_secure_token(ttl_minutes=self._ttl_days * 24 * 60)
        await self._repository.create(user_id=user_id, token_hash=token.token_hash, expires_at=token.expires_at)
        return IssuedSession(raw_token=token.raw_token, expires_at=token.expires_at)

    async def rotate(self, raw_token: str) -> tuple[int, IssuedSession]:
        """Validate a presented refresh token and rotate it.

        Returns (user_id, new_session). Raises InvalidRefreshTokenError for
        every failure mode (missing, unknown, expired, already-revoked) with
        an identical message, so a client can never distinguish them.
        """
        existing = await self._repository.get_by_token_hash(hash_token(raw_token))

        if existing is None:
            raise InvalidRefreshTokenError("Invalid or expired refresh token.")

        if existing.revoked_at is not None:
            if existing.replaced_by_id is not None:
                # This token was revoked *by being rotated into a new one* -
                # a legitimate client would already be using that new token,
                # so presenting the old one again means someone else has a
                # copy of it. Treat the whole account as compromised: revoke
                # every session, not just this chain, since we can't tell how
                # the token leaked.
                logger.warning(
                    "Refresh token replay detected; revoking all sessions.",
                    extra={"event": "refresh_token_replay", "user_id": existing.user_id},
                )
                await self._repository.revoke_all_for_user(existing.user_id, current_time())
                await self._repository.commit()
            # else: revoked via logout/logout-all/password-reset, or simply
            # expired-and-cleaned-up - reusing it just means a stale client,
            # not evidence of compromise, so reject only this request without
            # touching the user's other, still-legitimate sessions.
            raise InvalidRefreshTokenError("Invalid or expired refresh token.")

        if is_expired(existing.expires_at):
            await self._repository.revoke(existing, current_time())
            await self._repository.commit()
            raise InvalidRefreshTokenError("Invalid or expired refresh token.")

        new_token = generate_secure_token(ttl_minutes=self._ttl_days * 24 * 60)
        new_session = await self._repository.create(
            user_id=existing.user_id, token_hash=new_token.token_hash, expires_at=new_token.expires_at
        )
        await self._repository.revoke(existing, current_time(), replaced_by_id=new_session.id)
        await self._repository.commit()

        return existing.user_id, IssuedSession(raw_token=new_token.raw_token, expires_at=new_token.expires_at)

    async def revoke(self, raw_token: str) -> None:
        """Logout: revoke exactly the presented session, if it exists.

        Silently does nothing for a missing/unknown/already-revoked token -
        logout must always succeed from the caller's perspective (it never
        reveals whether a session existed).
        """
        existing = await self._repository.get_by_token_hash(hash_token(raw_token))
        if existing is None or existing.revoked_at is not None:
            return
        await self._repository.revoke(existing, current_time())
        await self._repository.commit()

    async def revoke_all_for_user(self, user_id: int) -> None:
        """Logout-all, and used after a successful password reset."""
        await self._repository.revoke_all_for_user(user_id, current_time())
        await self._repository.commit()
