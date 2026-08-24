"""Unit tests for Resend-backed email delivery."""
import asyncio
from functools import partial

import httpx
import pytest

from app.core.config import Settings
from app.services import email_service as email_service_module
from app.services.email_service import RESEND_API_URL, EmailService


def test_email_service_disabled_returns_false() -> None:
    settings = Settings(email_delivery_enabled=False)
    service = EmailService(settings)

    result = asyncio.run(
        service.send_verification_email(to_email="alice@example.com", raw_token="verification-token")
    )

    assert result is False


def test_email_service_requires_delivery_configuration() -> None:
    settings = Settings(
        email_delivery_enabled=True,
        resend_api_key="",
        email_from_address="",
    )
    service = EmailService(settings)

    result = asyncio.run(
        service.send_verification_email(to_email="alice@example.com", raw_token="verification-token")
    )

    assert result is False


def _settings() -> Settings:
    return Settings(
        email_delivery_enabled=True,
        resend_api_key="re_test_key",
        email_from_address="Masteacon <onboarding@masteacon.test>",
        frontend_base_url="http://localhost:5173",
    )


def test_send_verification_email_posts_to_resend_and_returns_true(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = request.read()
        return httpx.Response(200, json={"id": "email-id-123"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        email_service_module.httpx, "AsyncClient", partial(httpx.AsyncClient, transport=transport)
    )

    service = EmailService(_settings())
    result = asyncio.run(service.send_verification_email(to_email="alice@example.com", raw_token="tok-123"))

    assert result is True
    assert captured["url"] == RESEND_API_URL
    assert captured["auth"] == "Bearer re_test_key"
    assert b"tok-123" in captured["body"]
    assert b"alice@example.com" in captured["body"]


def test_send_verification_email_returns_false_on_delivery_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid api key"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        email_service_module.httpx, "AsyncClient", partial(httpx.AsyncClient, transport=transport)
    )

    service = EmailService(_settings())
    result = asyncio.run(service.send_verification_email(to_email="alice@example.com", raw_token="tok-123"))

    assert result is False
