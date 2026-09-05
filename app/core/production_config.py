"""Fail-fast validation for production configuration.

Development defaults exist throughout Settings so the app "just works" with
no `.env` at all. That is exactly the problem in production: it's entirely
possible to boot a real, internet-facing instance still using the insecure
JWT secret, the dev database password, localhost CORS origins, or a missing
required API key — each silently, until it causes a security incident or a
confusing runtime failure. This module collects every such check in one
place and is called once at startup: if APP_ENV=production and anything here
is wrong, the process refuses to start with a clear, actionable message
instead of serving traffic in a broken or insecure state.
"""
from app.core.config import Settings

INSECURE_DEFAULT_JWT_SECRET = "insecure-development-secret-change-me"
_DEV_DB_CREDENTIAL_MARKER = "postgres:postgres@"
_DEV_CORS_ORIGIN = "http://localhost:5173"


def validate_production_config(settings: Settings) -> list[str]:
    """Return a list of human-readable problems with `settings` for a
    production deployment. Empty means "safe to boot".
    """
    if settings.app_env != "production":
        return []

    errors: list[str] = []

    # --- JWT secret ---
    if settings.jwt_secret_key == INSECURE_DEFAULT_JWT_SECRET:
        errors.append(
            "JWT_SECRET_KEY is still set to the insecure default. Set a unique, "
            "secret value (e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`)."
        )

    # --- Database configuration ---
    if _DEV_DB_CREDENTIAL_MARKER in settings.database_url:
        errors.append(
            "DATABASE_URL still uses the default postgres/postgres credentials. Set a real "
            "POSTGRES_PASSWORD (docker-compose.yml builds DATABASE_URL from it automatically)."
        )

    # --- Required production credentials ---
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic.")
    if settings.email_delivery_enabled and not settings.resend_api_key:
        errors.append("RESEND_API_KEY is required when EMAIL_DELIVERY_ENABLED=true.")
    if settings.turnstile_enabled and not settings.turnstile_secret_key:
        errors.append("TURNSTILE_SECRET_KEY is required when TURNSTILE_ENABLED=true.")

    # --- Base URL / domain configuration ---
    if _DEV_CORS_ORIGIN in settings.cors_origins:
        errors.append(
            "CORS_ORIGINS still includes the local dev origin (http://localhost:5173). Set it "
            "to your real production origin(s), e.g. https://app.yourdomain.com."
        )
    if settings.frontend_base_url.startswith("http://localhost"):
        errors.append(
            "FRONTEND_BASE_URL still points at localhost. Set it to your real production "
            "origin — verification-email links are built from this value."
        )

    return errors
