"""Password reset: forgot-password request -> emailed single-use token -> reset.

Question -> forgot_password (enumeration-safe) -> emailed reset link ->
reset_password (single-use, hashed token) -> all of the user's refresh
sessions revoked, so a stolen password can't be used to keep an existing
session alive after the legitimate owner resets it.
"""
from app.core.exceptions import PasswordResetError
from app.core.logging import get_logger
from app.core.secure_token import current_time, generate_secure_token, hash_token, is_expired
from app.core.security import hash_password
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.services.refresh_session_service import RefreshSessionService

logger = get_logger(__name__)


class PasswordResetService:
    """Orchestrates the forgot-password / reset-password flow."""

    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository,
        refresh_session_service: RefreshSessionService,
        email_service: EmailService,
        ttl_minutes: int,
    ) -> None:
        self._users = user_repository
        self._reset_tokens = reset_token_repository
        self._refresh_sessions = refresh_session_service
        self._email_service = email_service
        self._ttl_minutes = ttl_minutes

    async def forgot_password(self, email: str) -> None:
        """Issue a reset token and email it — enumeration-safe: the caller
        gets the same (no) response whether or not the account exists.
        """
        user = await self._users.get_by_email(email)
        if user is None or not user.is_active:
            return

        token = generate_secure_token(ttl_minutes=self._ttl_minutes)
        await self._reset_tokens.create(user_id=user.id, token_hash=token.token_hash, expires_at=token.expires_at)
        await self._reset_tokens.commit()

        await self._email_service.send_password_reset_email(to_email=user.email, raw_token=token.raw_token)

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        """Consume a single-use reset token and set a new password.

        Revokes every one of the user's refresh sessions on success, so
        anyone who had a live session (e.g. via a stolen password) is
        logged out everywhere the moment the real owner resets it.
        """
        reset_token = await self._reset_tokens.get_by_token_hash(hash_token(raw_token))

        if reset_token is None or reset_token.used_at is not None or is_expired(reset_token.expires_at):
            raise PasswordResetError("Invalid or expired password reset token.")

        user = await self._users.get_by_id(reset_token.user_id)
        if user is None:
            raise PasswordResetError("Invalid or expired password reset token.")

        await self._users.update_password(user, hash_password(new_password))
        await self._reset_tokens.mark_used(reset_token, current_time())
        await self._users.commit()

        await self._refresh_sessions.revoke_all_for_user(user.id)

        logger.info(
            "Password reset completed; all sessions revoked.",
            extra={"event": "password_reset", "user_id": user.id},
        )
