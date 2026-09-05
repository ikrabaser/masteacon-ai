"""Shared helpers for generating and validating single-use, hashed secure tokens.

Used by refresh sessions and password reset (email verification has its own,
functionally-identical implementation predating this module — left alone
rather than refactored, per an explicit "don't change email verification
behavior" requirement). The pattern is always the same: hand the caller a
random token, persist only its SHA-256 hash, so a database leak alone can
never be turned into a working token.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets


@dataclass(frozen=True)
class SecureToken:
    raw_token: str
    token_hash: str
    expires_at: datetime


def generate_secure_token(ttl_minutes: int) -> SecureToken:
    raw_token = secrets.token_urlsafe(32)
    return SecureToken(
        raw_token=raw_token,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    )


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def current_time() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(expires_at: datetime) -> bool:
    return expires_at <= datetime.now(timezone.utc)
