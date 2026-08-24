"""Pydantic schemas for authentication endpoints."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request body for POST /api/v1/auth/register."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    # Hidden bot-trap field. Legitimate clients leave this empty.
    website: str = Field(default="", max_length=200)
    turnstile_token: str = Field(default="", max_length=2048)


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Response body for a successful login/registration."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public representation of a user (never includes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VerifyEmailRequest(BaseModel):
    """Request body for POST /api/v1/auth/verify-email."""

    token: str = Field(min_length=20, max_length=512)


class EmailVerificationResponse(BaseModel):
    """Response returned after successful email verification."""

    verified: bool = True
    message: str = "Email verified successfully."


class ResendVerificationRequest(BaseModel):
    """Request a fresh email-verification message."""

    email: EmailStr


class ResendVerificationResponse(BaseModel):
    """Enumeration-safe response for verification email requests."""

    message: str = (
        "If an eligible account exists for this email, "
        "a verification message has been sent."
    )
