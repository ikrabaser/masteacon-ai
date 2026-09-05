"""Tests for fail-fast production configuration validation."""
from app.core.config import Settings
from app.core.production_config import validate_production_config


def _settings(**overrides) -> Settings:
    defaults = {
        "app_env": "production",
        "jwt_secret_key": "a-real-random-secret-value",
        "database_url": "postgresql+asyncpg://realuser:realpass@db.internal:5432/masteacon",
        "openai_api_key": "sk-real-key",
        "cors_origins": "https://app.example.com",
        "frontend_base_url": "https://app.example.com",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_a_fully_valid_production_config_has_no_errors() -> None:
    assert validate_production_config(_settings()) == []


def test_development_env_is_never_validated() -> None:
    settings = _settings(app_env="development", jwt_secret_key="insecure-development-secret-change-me")

    assert validate_production_config(settings) == []


def test_rejects_the_default_jwt_secret() -> None:
    settings = _settings(jwt_secret_key="insecure-development-secret-change-me")

    errors = validate_production_config(settings)

    assert any("JWT_SECRET_KEY" in e for e in errors)


def test_rejects_the_default_database_credentials() -> None:
    settings = _settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_knowledge_assistant"
    )

    errors = validate_production_config(settings)

    assert any("DATABASE_URL" in e for e in errors)


def test_requires_an_openai_key_when_openai_is_the_provider() -> None:
    settings = _settings(llm_provider="openai", openai_api_key="")

    errors = validate_production_config(settings)

    assert any("OPENAI_API_KEY" in e for e in errors)


def test_requires_an_anthropic_key_only_when_anthropic_is_the_provider() -> None:
    openai_settings = _settings(llm_provider="openai", anthropic_api_key="")
    assert not any("ANTHROPIC_API_KEY" in e for e in validate_production_config(openai_settings))

    anthropic_settings = _settings(llm_provider="anthropic", anthropic_api_key="")
    assert any("ANTHROPIC_API_KEY" in e for e in validate_production_config(anthropic_settings))


def test_requires_a_resend_key_only_when_email_delivery_is_enabled() -> None:
    settings = _settings(email_delivery_enabled=True, resend_api_key="")

    errors = validate_production_config(settings)

    assert any("RESEND_API_KEY" in e for e in errors)


def test_requires_a_turnstile_secret_only_when_turnstile_is_enabled() -> None:
    settings = _settings(turnstile_enabled=True, turnstile_secret_key="")

    errors = validate_production_config(settings)

    assert any("TURNSTILE_SECRET_KEY" in e for e in errors)


def test_rejects_the_dev_cors_origin() -> None:
    settings = _settings(cors_origins="http://localhost:5173,http://localhost:3000")

    errors = validate_production_config(settings)

    assert any("CORS_ORIGINS" in e for e in errors)


def test_rejects_a_localhost_frontend_base_url() -> None:
    settings = _settings(frontend_base_url="http://localhost:5173")

    errors = validate_production_config(settings)

    assert any("FRONTEND_BASE_URL" in e for e in errors)


def test_reports_every_problem_at_once_not_just_the_first() -> None:
    settings = _settings(
        jwt_secret_key="insecure-development-secret-change-me",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_knowledge_assistant",
        openai_api_key="",
    )

    errors = validate_production_config(settings)

    assert len(errors) >= 3
