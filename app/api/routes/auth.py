"""Authentication endpoints: register, login, refresh/logout sessions,
password reset, current-user lookup.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_current_user,
    get_password_reset_service,
    get_refresh_session_service,
    get_settings,
    get_turnstile_service,
)
from app.core.client_ip import get_client_ip
from app.core.config import Settings
from app.core.exceptions import InvalidRefreshTokenError
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    EmailVerificationResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_protection_service import AuthProtectionService
from app.services.auth_service import AuthService
from app.services.password_reset_service import PasswordResetService
from app.services.refresh_session_service import IssuedSession, RefreshSessionService
from app.services.turnstile_service import TurnstileService


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Scoped to the auth prefix only — the cookie is never sent on unrelated API
# calls (documents, chat, etc.), which both limits exposure and narrows the
# CSRF surface to just these few endpoints. See README's Security Notes for
# the full CSRF reasoning (SameSite=Lax + this scoping + CORS + the fact that
# a cross-site caller can never read the JSON response body it would need).
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _client_identifier(request: Request, settings: Settings) -> str:
    return get_client_ip(request, settings.trusted_proxy_count)


def _set_refresh_cookie(response: Response, settings: Settings, session: IssuedSession) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=session.raw_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
    )


async def _enforce_rate_limit(
    *,
    protection: AuthProtectionService,
    action: str,
    identifier: str,
) -> None:
    result = await protection.check_rate_limit(
        action=action,
        identifier=identifier,
    )

    if result.allowed:
        return

    raise HTTPException(
        status_code=429,
        detail="Too many authentication attempts. Please try again later.",
        headers={"Retry-After": str(result.retry_after)},
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    http_request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    protection: AuthProtectionService = Depends(get_auth_protection_service),
    turnstile: TurnstileService = Depends(get_turnstile_service),
    refresh_sessions: RefreshSessionService = Depends(get_refresh_session_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Create a new user account, start a session, and return an access token."""

    identifier = _client_identifier(http_request, settings)

    await _enforce_rate_limit(
        protection=protection,
        action="register",
        identifier=identifier,
    )

    if protection.is_honeypot_triggered(payload.website):
        raise HTTPException(
            status_code=400,
            detail="Invalid registration request.",
        )

    verification = await turnstile.verify(
        token=payload.turnstile_token,
        remote_ip=identifier,
    )

    if not verification.success:
        raise HTTPException(
            status_code=400,
            detail="Turnstile verification failed.",
        )

    user, token, _verification_token = await auth_service.register(
        email=payload.email,
        password=payload.password,
    )

    session = await refresh_sessions.issue(user.id)
    _set_refresh_cookie(response, settings, session)

    return TokenResponse(access_token=token)


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
)
async def resend_verification(
    payload: ResendVerificationRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    protection: AuthProtectionService = Depends(get_auth_protection_service),
    settings: Settings = Depends(get_settings),
) -> ResendVerificationResponse:
    """Request a fresh verification email without exposing account existence."""

    identifier = _client_identifier(http_request, settings)

    await _enforce_rate_limit(
        protection=protection,
        action="register",
        identifier=identifier,
    )

    await auth_service.resend_verification(payload.email)

    return ResendVerificationResponse()


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
)
async def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> EmailVerificationResponse:
    """Verify ownership of the email address for a registered account."""

    await auth_service.verify_email(payload.token)

    return EmailVerificationResponse()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    http_request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    protection: AuthProtectionService = Depends(get_auth_protection_service),
    refresh_sessions: RefreshSessionService = Depends(get_refresh_session_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate with email/password, start a session, and return an access token."""

    identifier = _client_identifier(http_request, settings)

    await _enforce_rate_limit(
        protection=protection,
        action="login",
        identifier=identifier,
    )

    user, token = await auth_service.login(
        email=payload.email,
        password=payload.password,
    )

    # A valid login ends the current failed-attempt window for this client.
    await protection.reset_rate_limit(
        action="login",
        identifier=identifier,
    )

    session = await refresh_sessions.issue(user.id)
    _set_refresh_cookie(response, settings, session)

    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    http_request: Request,
    response: Response,
    refresh_sessions: RefreshSessionService = Depends(get_refresh_session_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Rotate the refresh session (from its HttpOnly cookie) and issue a new
    short-lived access token. The old refresh token stops working the moment
    this succeeds — presenting it again is treated as a replay (see
    RefreshSessionService.rotate) and revokes every session for the account.
    """
    raw_token = http_request.cookies.get(settings.refresh_cookie_name)
    if not raw_token:
        raise InvalidRefreshTokenError("Invalid or expired refresh token.")

    user_id, new_session = await refresh_sessions.rotate(raw_token)
    _set_refresh_cookie(response, settings, new_session)

    access_token = create_access_token(subject=str(user_id), settings=settings)
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=204)
async def logout(
    http_request: Request,
    response: Response,
    refresh_sessions: RefreshSessionService = Depends(get_refresh_session_service),
    settings: Settings = Depends(get_settings),
) -> None:
    """Revoke the current session (if any) and clear the refresh cookie.

    Always succeeds, even with no cookie or an already-invalid one — logout
    never reveals whether a session existed.
    """
    raw_token = http_request.cookies.get(settings.refresh_cookie_name)
    if raw_token:
        await refresh_sessions.revoke(raw_token)

    _clear_refresh_cookie(response, settings)


@router.post("/logout-all", status_code=204)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    refresh_sessions: RefreshSessionService = Depends(get_refresh_session_service),
    settings: Settings = Depends(get_settings),
) -> None:
    """Revoke every session for the authenticated user (requires a still-valid
    access token), and clear this browser's refresh cookie."""
    await refresh_sessions.revoke_all_for_user(current_user.id)
    _clear_refresh_cookie(response, settings)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    http_request: Request,
    protection: AuthProtectionService = Depends(get_auth_protection_service),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
    settings: Settings = Depends(get_settings),
) -> ForgotPasswordResponse:
    """Request a password reset email — enumeration-safe: always the same response."""

    identifier = _client_identifier(http_request, settings)
    # Reuses the register bucket's limits — this endpoint has the same abuse
    # shape (unauthenticated, one email address per request, no useful
    # response to brute-force) as registration, not login.
    await _enforce_rate_limit(protection=protection, action="register", identifier=identifier)

    await password_reset_service.forgot_password(payload.email)

    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> ResetPasswordResponse:
    """Consume a single-use password reset token and set a new password.

    Revokes every refresh session for the account on success (see
    PasswordResetService.reset_password), so the client should treat any
    stored access token as invalid too and prompt for a fresh login.
    """
    await password_reset_service.reset_password(payload.token, payload.new_password)

    return ResetPasswordResponse()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user."""

    return UserResponse.model_validate(current_user)
