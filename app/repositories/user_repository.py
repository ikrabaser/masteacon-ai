"""Data-access layer for the User model."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Encapsulates all database queries related to User rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash, is_active=True)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def set_email_verification(
        self,
        user: User,
        token_hash: str,
        expires_at: datetime,
    ) -> User:
        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = expires_at
        user.is_email_verified = False
        user.email_verified_at = None

        await self._session.flush()
        return user

    async def get_by_verification_token_hash(
        self,
        token_hash: str,
    ) -> User | None:
        result = await self._session.execute(
            select(User).where(
                User.email_verification_token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def mark_email_verified(
        self,
        user: User,
        verified_at: datetime,
    ) -> User:
        user.is_email_verified = True
        user.email_verified_at = verified_at
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None

        await self._session.flush()
        return user

    async def update_password(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        await self._session.flush()
        return user

    async def commit(self) -> None:
        await self._session.commit()
