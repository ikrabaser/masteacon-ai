"""Unit tests for SMTP email delivery."""

from app.core.config import Settings
from app.services.email_service import EmailService


def test_email_service_disabled_returns_false() -> None:
    settings = Settings(
        email_delivery_enabled=False,
    )
    service = EmailService(settings)

    import asyncio

    result = asyncio.run(
        service.send_verification_email(
            to_email="alice@example.com",
            raw_token="verification-token",
        )
    )

    assert result is False


def test_email_service_requires_delivery_configuration() -> None:
    settings = Settings(
        email_delivery_enabled=True,
        smtp_host="",
        email_from_address="",
    )
    service = EmailService(settings)

    import asyncio

    result = asyncio.run(
        service.send_verification_email(
            to_email="alice@example.com",
            raw_token="verification-token",
        )
    )

    assert result is False
