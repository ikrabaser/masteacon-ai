"""Tests for AuthService: registration, login and password/token behavior."""
import pytest

from app.core.config import Settings
from app.core.exceptions import InactiveUserError, InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import decode_access_token
from app.services.auth_service import AuthService
from tests.fakes import FakeUserRepository


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret_key="test-secret", jwt_algorithm="HS256", access_token_expire_minutes=60)


@pytest.fixture
def auth_service(settings: Settings) -> AuthService:
    return AuthService(user_repository=FakeUserRepository(), settings=settings)


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_valid_token(auth_service: AuthService, settings: Settings) -> None:
    user, token, verification_token = await auth_service.register(email="alice@example.com", password="password123")

    assert user.email == "alice@example.com"
    assert user.password_hash != "password123"
    assert decode_access_token(token, settings) == str(user.id)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(auth_service: AuthService) -> None:
    await auth_service.register(email="alice@example.com", password="password123")

    with pytest.raises(UserAlreadyExistsError):
        await auth_service.register(email="alice@example.com", password="another-password")


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_credentials(auth_service: AuthService) -> None:
    registered_user, _, _ = await auth_service.register(email="bob@example.com", password="password123")
    registered_user.is_email_verified = True

    user, token = await auth_service.login(email="bob@example.com", password="password123")

    assert user.id == registered_user.id
    assert token


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(auth_service: AuthService) -> None:
    await auth_service.register(email="bob@example.com", password="password123")

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(email="bob@example.com", password="wrong-password")


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(auth_service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(email="nobody@example.com", password="whatever")


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(auth_service: AuthService) -> None:
    user, _, _ = await auth_service.register(email="carol@example.com", password="password123")
    user.is_active = False

    with pytest.raises(InactiveUserError):
        await auth_service.login(email="carol@example.com", password="password123")


@pytest.mark.asyncio
async def test_register_generates_and_stores_email_verification_token(
    settings: Settings,
) -> None:
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    users = FakeUserRepository()
    verification_service = EmailVerificationService(ttl_minutes=30)

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification_service,
    )

    user, token, verification_token = await service.register(
        email="verify@example.com",
        password="password123",
    )

    assert token
    assert verification_token is not None
    assert user.is_email_verified is False
    assert user.email_verification_token_hash is not None
    assert user.email_verification_expires_at is not None

    expected_hash = verification_service.hash_token(verification_token)

    assert user.email_verification_token_hash == expected_hash


@pytest.mark.asyncio
async def test_verify_email_marks_user_as_verified(
    settings: Settings,
) -> None:
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    users = FakeUserRepository()
    verification_service = EmailVerificationService(ttl_minutes=30)

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification_service,
    )

    user, _, raw_token = await service.register(
        email="verify-success@example.com",
        password="password123",
    )

    assert raw_token is not None

    verified_user = await service.verify_email(raw_token)

    assert verified_user.id == user.id
    assert verified_user.is_email_verified is True
    assert verified_user.email_verified_at is not None
    assert verified_user.email_verification_token_hash is None
    assert verified_user.email_verification_expires_at is None


@pytest.mark.asyncio
async def test_verify_email_rejects_invalid_token(
    settings: Settings,
) -> None:
    from app.core.exceptions import EmailVerificationError
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    service = AuthService(
        user_repository=FakeUserRepository(),
        settings=settings,
        email_verification_service=EmailVerificationService(),
    )

    with pytest.raises(
        EmailVerificationError,
        match="Invalid email verification token",
    ):
        await service.verify_email(
            "this-is-an-invalid-verification-token"
        )


@pytest.mark.asyncio
async def test_verify_email_rejects_expired_token(
    settings: Settings,
) -> None:
    from datetime import datetime, timedelta, timezone

    from app.core.exceptions import EmailVerificationError
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    users = FakeUserRepository()
    verification_service = EmailVerificationService(ttl_minutes=30)

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification_service,
    )

    user, _, raw_token = await service.register(
        email="expired@example.com",
        password="password123",
    )

    assert raw_token is not None

    user.email_verification_expires_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    with pytest.raises(
        EmailVerificationError,
        match="has expired",
    ):
        await service.verify_email(raw_token)


@pytest.mark.asyncio
async def test_email_verification_token_cannot_be_reused(
    settings: Settings,
) -> None:
    from app.core.exceptions import EmailVerificationError
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    users = FakeUserRepository()
    verification_service = EmailVerificationService(ttl_minutes=30)

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification_service,
    )

    _, _, raw_token = await service.register(
        email="single-use@example.com",
        password="password123",
    )

    assert raw_token is not None

    # First use succeeds.
    await service.verify_email(raw_token)

    # mark_email_verified() clears the stored token hash,
    # so the same raw token must no longer resolve to a user.
    with pytest.raises(
        EmailVerificationError,
        match="Invalid email verification token",
    ):
        await service.verify_email(raw_token)


@pytest.mark.asyncio
async def test_register_dispatches_verification_email(
    settings: Settings,
) -> None:
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    class FakeEmailService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def send_verification_email(
            self,
            *,
            to_email: str,
            raw_token: str,
        ) -> bool:
            self.calls.append((to_email, raw_token))
            return True

    users = FakeUserRepository()
    verification = EmailVerificationService(ttl_minutes=30)
    email_service = FakeEmailService()

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification,
        email_service=email_service,
    )

    user, _, raw_token = await service.register(
        email="mail-dispatch@example.com",
        password="password123",
    )

    assert raw_token is not None

    assert email_service.calls == [
        (
            user.email,
            raw_token,
        )
    ]

    # Only the hash belongs in persistent user state.
    assert user.email_verification_token_hash == (
        verification.hash_token(raw_token)
    )


@pytest.mark.asyncio
async def test_resend_verification_rotates_token_and_sends_email(
    settings: Settings,
) -> None:
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    class FakeEmailService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def send_verification_email(
            self,
            *,
            to_email: str,
            raw_token: str,
        ) -> bool:
            self.calls.append((to_email, raw_token))
            return True

    users = FakeUserRepository()
    verification = EmailVerificationService(ttl_minutes=30)
    email_service = FakeEmailService()

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification,
        email_service=email_service,
    )

    user, _, original_token = await service.register(
        email="resend@example.com",
        password="password123",
    )

    assert original_token is not None

    email_service.calls.clear()

    await service.resend_verification("resend@example.com")

    assert len(email_service.calls) == 1

    sent_email, new_token = email_service.calls[0]

    assert sent_email == user.email
    assert new_token != original_token
    assert user.email_verification_token_hash == (
        verification.hash_token(new_token)
    )


@pytest.mark.asyncio
async def test_resend_verification_is_safe_for_unknown_email(
    settings: Settings,
) -> None:
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    class FakeEmailService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def send_verification_email(
            self,
            *,
            to_email: str,
            raw_token: str,
        ) -> bool:
            self.calls.append((to_email, raw_token))
            return True

    email_service = FakeEmailService()

    service = AuthService(
        user_repository=FakeUserRepository(),
        settings=settings,
        email_verification_service=EmailVerificationService(
            ttl_minutes=30
        ),
        email_service=email_service,
    )

    result = await service.resend_verification(
        "does-not-exist@example.com"
    )

    assert result is None
    assert email_service.calls == []


@pytest.mark.asyncio
async def test_resend_verification_does_nothing_for_verified_user(
    settings: Settings,
) -> None:
    from app.services.email_verification_service import EmailVerificationService
    from tests.fakes import FakeUserRepository

    class FakeEmailService:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        async def send_verification_email(
            self,
            *,
            to_email: str,
            raw_token: str,
        ) -> bool:
            self.calls.append((to_email, raw_token))
            return True

    users = FakeUserRepository()
    verification = EmailVerificationService(ttl_minutes=30)
    email_service = FakeEmailService()

    service = AuthService(
        user_repository=users,
        settings=settings,
        email_verification_service=verification,
        email_service=email_service,
    )

    user, _, token = await service.register(
        email="verified@example.com",
        password="password123",
    )

    assert token is not None

    await service.verify_email(token)

    assert user.is_email_verified is True

    email_service.calls.clear()

    await service.resend_verification("verified@example.com")

    assert email_service.calls == []


@pytest.mark.asyncio
async def test_login_rejects_unverified_email(
    auth_service: AuthService,
) -> None:
    from app.core.exceptions import EmailNotVerifiedError

    await auth_service.register(
        email="unverified@example.com",
        password="password123",
    )

    with pytest.raises(
        EmailNotVerifiedError,
        match="verify your email",
    ):
        await auth_service.login(
            email="unverified@example.com",
            password="password123",
        )
