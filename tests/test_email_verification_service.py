"""Unit tests for email verification token handling."""

from datetime import datetime, timedelta, timezone

from app.services.email_verification_service import (
    EmailVerificationService,
)


def test_create_token_returns_raw_token_hash_and_expiry() -> None:
    service = EmailVerificationService(ttl_minutes=30)

    token = service.create_token()

    assert token.raw_token
    assert len(token.token_hash) == 64
    assert token.token_hash == service.hash_token(token.raw_token)
    assert token.expires_at > datetime.now(timezone.utc)


def test_create_token_generates_unique_tokens() -> None:
    service = EmailVerificationService()

    first = service.create_token()
    second = service.create_token()

    assert first.raw_token != second.raw_token
    assert first.token_hash != second.token_hash


def test_hash_token_is_deterministic() -> None:
    service = EmailVerificationService()

    first = service.hash_token("same-token")
    second = service.hash_token("same-token")

    assert first == second


def test_is_expired_returns_true_for_past_timestamp() -> None:
    service = EmailVerificationService()

    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert service.is_expired(expired_at) is True


def test_is_expired_returns_false_for_future_timestamp() -> None:
    service = EmailVerificationService()

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    assert service.is_expired(expires_at) is False
