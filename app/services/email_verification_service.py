"""Email verification token generation and validation helpers."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets


@dataclass(frozen=True)
class EmailVerificationToken:
    raw_token: str
    token_hash: str
    expires_at: datetime


class EmailVerificationService:
    """Generate and validate secure email verification tokens."""

    def __init__(self, ttl_minutes: int = 30) -> None:
        self._ttl_minutes = ttl_minutes

    def create_token(self) -> EmailVerificationToken:
        raw_token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._ttl_minutes,
        )

        return EmailVerificationToken(
            raw_token=raw_token,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def current_time() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        return expires_at <= datetime.now(timezone.utc)
