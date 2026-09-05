"""Data-access layer for RefreshSession."""
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_session import RefreshSession


class RefreshSessionRepository:
    """Encapsulates all database queries related to RefreshSession rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshSession:
        refresh_session = RefreshSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(refresh_session)
        await self._session.flush()
        await self._session.refresh(refresh_session)
        return refresh_session

    async def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        result = await self._session.execute(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, refresh_session: RefreshSession, revoked_at: datetime, replaced_by_id: int | None = None) -> None:
        refresh_session.revoked_at = revoked_at
        if replaced_by_id is not None:
            refresh_session.replaced_by_id = replaced_by_id
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> None:
        """Used by logout-all and by a successful password reset."""
        await self._session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
