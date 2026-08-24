"""Email delivery service for account verification messages."""

import asyncio
from email.message import EmailMessage
import smtplib
from urllib.parse import urlencode

from app.core.config import Settings


class EmailService:
    """Send transactional authentication emails through SMTP."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.email_delivery_enabled
        self._smtp_host = settings.smtp_host
        self._smtp_port = settings.smtp_port
        self._smtp_username = settings.smtp_username
        self._smtp_password = settings.smtp_password
        self._smtp_use_tls = settings.smtp_use_tls
        self._from_address = settings.email_from_address
        self._frontend_base_url = settings.frontend_base_url.rstrip("/")

    async def send_verification_email(
        self,
        *,
        to_email: str,
        raw_token: str,
    ) -> bool:
        """Send an email-verification link.

        Returns False when delivery is disabled. SMTP work is delegated to a
        thread so synchronous smtplib does not block the FastAPI event loop.
        """

        if not self._enabled:
            return False

        if not self._smtp_host or not self._from_address:
            return False

        query = urlencode({"token": raw_token})
        verification_url = (
            f"{self._frontend_base_url}/verify-email?{query}"
        )

        message = EmailMessage()
        message["Subject"] = "Verify your Masteacon email"
        message["From"] = self._from_address
        message["To"] = to_email

        message.set_content(
            "Welcome to Masteacon.\n\n"
            "Verify your email address using the link below:\n\n"
            f"{verification_url}\n\n"
            "If you did not create this account, you can ignore this email."
        )

        await asyncio.to_thread(
            self._send_message,
            message,
        )

        return True

    def _send_message(self, message: EmailMessage) -> None:
        with smtplib.SMTP(
            self._smtp_host,
            self._smtp_port,
            timeout=10,
        ) as smtp:
            if self._smtp_use_tls:
                smtp.starttls()

            if self._smtp_username:
                smtp.login(
                    self._smtp_username,
                    self._smtp_password,
                )

            smtp.send_message(message)
