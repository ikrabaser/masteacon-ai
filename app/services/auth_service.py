"""Registration, login and token issuance."""
from app.core.config import Settings
from app.core.exceptions import (
    EmailNotVerifiedError,
    EmailVerificationError,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.email_verification_service import EmailVerificationService
from app.services.email_service import EmailService


class AuthService:
    """Orchestrates user registration and login against the UserRepository."""

    def __init__(
        self,
        user_repository: UserRepository,
        settings: Settings,
        email_verification_service: EmailVerificationService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self._users = user_repository
        self._settings = settings
        self._email_verification = email_verification_service
        self._email_service = email_service

    async def register(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str, str | None]:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(f"An account with email '{email}' already exists.")

        user = await self._users.create(
            email=email,
            password_hash=hash_password(password),
        )

        raw_verification_token: str | None = None

        if self._email_verification is not None:
            verification = self._email_verification.create_token()

            await self._users.set_email_verification(
                user=user,
                token_hash=verification.token_hash,
                expires_at=verification.expires_at,
            )

            raw_verification_token = verification.raw_token

        await self._users.commit()

        if (
            raw_verification_token is not None
            and self._email_service is not None
        ):
            await self._email_service.send_verification_email(
                to_email=user.email,
                raw_token=raw_verification_token,
            )

        token = create_access_token(
            subject=str(user.id),
            settings=self._settings,
        )

        return user, token, raw_verification_token

    async def verify_email(self, raw_token: str) -> User:
        if self._email_verification is None:
            raise EmailVerificationError(
                "Email verification is not available."
            )

        token_hash = self._email_verification.hash_token(
            raw_token.strip()
        )

        user = await self._users.get_by_verification_token_hash(
            token_hash
        )

        if user is None:
            raise EmailVerificationError(
                "Invalid email verification token."
            )

        expires_at = user.email_verification_expires_at

        if (
            expires_at is None
            or self._email_verification.is_expired(expires_at)
        ):
            raise EmailVerificationError(
                "Email verification token has expired."
            )

        await self._users.mark_email_verified(
            user=user,
            verified_at=self._email_verification.current_time(),
        )
        await self._users.commit()

        return user

    async def resend_verification(self, email: str) -> None:
        """Issue a fresh verification token without revealing account state."""

        user = await self._users.get_by_email(email)

        # Enumeration-safe behavior:
        # callers receive the same response whether the account exists or not.
        if user is None:
            return

        # Already verified accounts do not need another token.
        if user.is_email_verified:
            return

        if (
            self._email_verification is None
            or self._email_service is None
        ):
            return

        verification = self._email_verification.create_token()

        await self._users.set_email_verification(
            user=user,
            token_hash=verification.token_hash,
            expires_at=verification.expires_at,
        )
        await self._users.commit()

        await self._email_service.send_verification_email(
            to_email=user.email,
            raw_token=verification.raw_token,
        )

    async def login(self, email: str, password: str) -> tuple[User, str]:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        if not user.is_active:
            raise InactiveUserError("This account has been deactivated.")

        if not user.is_email_verified:
            raise EmailNotVerifiedError(
                "Please verify your email address before signing in."
            )

        token = create_access_token(subject=str(user.id), settings=self._settings)
        return user, token
