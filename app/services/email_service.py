"""Email delivery service for account verification messages, via the Resend API.

Resend (https://resend.com) is a transactional email API: a single authenticated
HTTPS call, no SMTP server, no mailbox app-password to manage. `httpx` (already a
project dependency) is used directly rather than pulling in Resend's own SDK, to
avoid an extra dependency for what is a two-field JSON POST.
"""
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _verification_email_html(verification_url: str) -> str:
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:32px 16px;background:#0b0f14;font-family:-apple-system,
    BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0"
            style="background:#12181f;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:32px 32px 24px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:#e8edf3;letter-spacing:-0.02em;">
                  Masteacon
                </div>
                <div style="font-size:13px;color:#8b98a8;margin-top:4px;">
                  Your beacon to mastery.
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px;">
                <h1 style="font-size:18px;color:#e8edf3;margin:0 0 12px;">Verify your email</h1>
                <p style="font-size:14px;line-height:1.6;color:#b6c0cc;margin:0 0 24px;">
                  Welcome to Masteacon. Confirm this is your email address to finish
                  setting up your account.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 28px;">
                <a href="{verification_url}"
                  style="display:inline-block;background:#4f8cff;color:#ffffff;
                  font-size:14px;font-weight:600;text-decoration:none;padding:12px 24px;
                  border-radius:8px;">
                  Verify email address
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 32px;">
                <p style="font-size:12px;line-height:1.6;color:#6b7688;margin:0;">
                  If the button doesn't work, copy and paste this link into your browser:<br>
                  <a href="{verification_url}" style="color:#4f8cff;word-break:break-all;">
                    {verification_url}
                  </a>
                </p>
                <p style="font-size:12px;line-height:1.6;color:#6b7688;margin:16px 0 0;">
                  If you did not create this account, you can safely ignore this email.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _verification_email_text(verification_url: str) -> str:
    return (
        "Welcome to Masteacon.\n\n"
        "Verify your email address using the link below:\n\n"
        f"{verification_url}\n\n"
        "If you did not create this account, you can ignore this email."
    )


def _password_reset_email_html(reset_url: str) -> str:
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:32px 16px;background:#0b0f14;font-family:-apple-system,
    BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0"
            style="background:#12181f;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:32px 32px 24px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:#e8edf3;letter-spacing:-0.02em;">
                  Masteacon
                </div>
                <div style="font-size:13px;color:#8b98a8;margin-top:4px;">
                  Your beacon to mastery.
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px;">
                <h1 style="font-size:18px;color:#e8edf3;margin:0 0 12px;">Reset your password</h1>
                <p style="font-size:14px;line-height:1.6;color:#b6c0cc;margin:0 0 24px;">
                  We received a request to reset your Masteacon password. This link expires
                  soon and can only be used once.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 28px;">
                <a href="{reset_url}"
                  style="display:inline-block;background:#4f8cff;color:#ffffff;
                  font-size:14px;font-weight:600;text-decoration:none;padding:12px 24px;
                  border-radius:8px;">
                  Reset password
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 32px;">
                <p style="font-size:12px;line-height:1.6;color:#6b7688;margin:0;">
                  If the button doesn't work, copy and paste this link into your browser:<br>
                  <a href="{reset_url}" style="color:#4f8cff;word-break:break-all;">
                    {reset_url}
                  </a>
                </p>
                <p style="font-size:12px;line-height:1.6;color:#6b7688;margin:16px 0 0;">
                  If you did not request this, you can safely ignore this email — your
                  password will not be changed.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _password_reset_email_text(reset_url: str) -> str:
    return (
        "We received a request to reset your Masteacon password.\n\n"
        "Reset it using the link below (expires soon, single use):\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email — your password will not change."
    )


class EmailService:
    """Send transactional authentication emails through the Resend API."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.email_delivery_enabled
        self._api_key = settings.resend_api_key
        self._from_address = settings.email_from_address
        self._frontend_base_url = settings.frontend_base_url.rstrip("/")

    async def send_verification_email(
        self,
        *,
        to_email: str,
        raw_token: str,
    ) -> bool:
        """Send an email-verification link.

        Returns False when delivery is disabled or misconfigured, so callers
        (AuthService) can treat email delivery as best-effort and never let it
        block registration.
        """
        if not self._enabled:
            return False

        if not self._api_key or not self._from_address:
            logger.warning(
                "Email delivery is enabled but RESEND_API_KEY or EMAIL_FROM_ADDRESS is missing; "
                "skipping verification email."
            )
            return False

        query = urlencode({"token": raw_token})
        verification_url = f"{self._frontend_base_url}/verify-email?{query}"

        return await self._send(
            to_email=to_email,
            subject="Verify your Masteacon email",
            html=_verification_email_html(verification_url),
            text=_verification_email_text(verification_url),
            log_label="verification",
        )

    async def send_password_reset_email(
        self,
        *,
        to_email: str,
        raw_token: str,
    ) -> bool:
        """Send a password-reset link. Same best-effort contract as above:
        returns False when delivery is disabled/misconfigured/fails, never
        raises — a reset request must never block or leak whether the email
        actually went out.
        """
        if not self._enabled:
            return False

        if not self._api_key or not self._from_address:
            logger.warning(
                "Email delivery is enabled but RESEND_API_KEY or EMAIL_FROM_ADDRESS is missing; "
                "skipping password reset email."
            )
            return False

        query = urlencode({"token": raw_token})
        reset_url = f"{self._frontend_base_url}/reset-password?{query}"

        return await self._send(
            to_email=to_email,
            subject="Reset your Masteacon password",
            html=_password_reset_email_html(reset_url),
            text=_password_reset_email_text(reset_url),
            log_label="password reset",
        )

    async def _send(self, *, to_email: str, subject: str, html: str, text: str, log_label: str) -> bool:
        payload = {
            "from": self._from_address,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # Delivery failures are logged, never raised — the caller's flow
            # (registration, password reset, ...) must not fail just because
            # the email couldn't be sent.
            logger.warning("Failed to send %s email via Resend: %s", log_label, exc)
            return False

        return True
