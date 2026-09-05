"""Domain-specific exceptions used across services and translated to HTTP responses."""


class AppError(Exception):
    """Base class for all handled application errors."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFileTypeError(AppError):
    """Raised when an uploaded file's extension/content-type is not supported."""

    status_code = 415


class FileTooLargeError(AppError):
    """Raised when an uploaded file exceeds the configured size limit."""

    status_code = 413


class DocumentNotFoundError(AppError):
    """Raised when a requested document id does not exist."""

    status_code = 404


class ParsingError(AppError):
    """Raised when text extraction from a document fails (corrupt/empty/unreadable)."""

    status_code = 422


class EmbeddingProviderError(AppError):
    """Raised when the embedding provider (OpenAI) fails or times out."""

    status_code = 502


class ChatProviderError(AppError):
    """Raised when the chat completion provider (OpenAI/Anthropic) fails or times out."""

    status_code = 502


class UserAlreadyExistsError(AppError):
    """Raised when registering with an email that is already taken."""

    status_code = 409


class InvalidCredentialsError(AppError):
    """Raised when login credentials are wrong, or a token is missing/invalid/expired."""

    status_code = 401


class InactiveUserError(AppError):
    """Raised when an authenticated user's account has been deactivated."""

    status_code = 403


class WorkspaceNotFoundError(AppError):
    """Raised when a requested workspace id does not exist or is not owned by the caller."""

    status_code = 404


class ConversationNotFoundError(AppError):
    """Raised when a requested conversation id does not exist or is not owned by the caller."""

    status_code = 404


class ToolExecutionError(AppError):
    """Raised when a requested LLM tool call is unknown, invalid, or fails to execute."""

    status_code = 422


class EmailVerificationError(AppError):
    """Raised when an email verification token is invalid or expired."""

    status_code = 400


class EmailNotVerifiedError(AppError):
    """Raised when login is attempted before email verification."""

    status_code = 403


class InvalidRefreshTokenError(AppError):
    """Raised when a refresh token is missing, unknown, expired, or revoked.

    Deliberately uses the same generic message/status for every one of those
    cases (missing cookie, unknown hash, expired, already-rotated/replayed)
    so a client can never distinguish "no session" from "a stolen, replayed
    token" from the response alone.
    """

    status_code = 401


class PasswordResetError(AppError):
    """Raised when a password-reset token is invalid, expired, or already used."""

    status_code = 400
