"""Authentication endpoints: register, login, current-user lookup."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import (
    get_auth_protection_service,
    get_auth_service,
    get_current_user,
    get_settings,
    get_turnstile_service,
)
from app.core.client_ip import get_client_ip
from app.core.config import Settings
from app.models.user import User
from app.schemas.auth import (
    EmailVerificationResponse,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_protection_service import AuthProtectionService
from app.services.auth_service import AuthService
from app.services.turnstile_service import TurnstileService


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_identifier(request: Request, settings: Settings) -> str:
    return get_client_ip(request, settings.trusted_proxy_count)


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
    auth_service: AuthService = Depends(get_auth_service),
    protection: AuthProtectionService = Depends(get_auth_protection_service),
    turnstile: TurnstileService = Depends(get_turnstile_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Create a new user account and return an access token."""

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

    _, token, _verification_token = await auth_service.register(
        email=payload.email,
        password=payload.password,
    )

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
    auth_service: AuthService = Depends(get_auth_service),
    protection: AuthProtectionService = Depends(get_auth_protection_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate with email/password and return an access token."""

    identifier = _client_identifier(http_request, settings)

    await _enforce_rate_limit(
        protection=protection,
        action="login",
        identifier=identifier,
    )

    _, token = await auth_service.login(
        email=payload.email,
        password=payload.password,
    )

    # A valid login ends the current failed-attempt window for this client.
    await protection.reset_rate_limit(
        action="login",
        identifier=identifier,
    )

    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user."""

    return UserResponse.model_validate(current_user)
