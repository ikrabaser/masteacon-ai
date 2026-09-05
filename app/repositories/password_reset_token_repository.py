"""Data-access layer for PasswordResetToken."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    """Encapsulates all database queries related to PasswordResetToken rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> PasswordResetToken:
        reset_token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(reset_token)
        await self._session.flush()
        return reset_token

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, reset_token: PasswordResetToken, used_at: datetime) -> None:
        reset_token.used_at = used_at
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
