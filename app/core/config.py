"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, sourced from the environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "AI Knowledge Assistant"
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_knowledge_assistant"

    # Redis — Celery broker/result backend for asynchronous document indexing
    redis_url: str = "redis://localhost:6379/0"

    # LLM provider selection — "openai" or "anthropic". Embeddings always use OpenAI
    # (Anthropic has no public embeddings API), only chat/generation is switched.
    llm_provider: str = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-3-5-sonnet-20241022"

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 150

    # Retrieval
    search_top_k: int = 5
    similarity_threshold: float = 0.3

    # Query rewriting — an LLM call that expands a user's raw (often terse or
    # informal) question into a retrieval-optimized query before it's embedded
    # / keyword-searched. Disabled by default: an extra LLM round-trip per
    # question means added latency and cost, and off means byte-for-byte the
    # same retrieval behavior as before.
    query_rewriting_enabled: bool = False

    # Groundedness check — an extra LLM-judge call (reusing the same
    # Faithfulness scorer as `scripts/run_rag_evaluation.py`) that verifies a
    # generated answer's claims are actually supported by the retrieved
    # context, live, on every request. Below `groundedness_threshold`, the
    # answer is replaced with an explicit "not enough evidence" message
    # instead of risking an unsupported claim reaching the user. Disabled by
    # default: an extra LLM round-trip per question means added latency and
    # cost, same trade-off as query rewriting.
    groundedness_check_enabled: bool = False
    groundedness_threshold: float = 0.5

    # Reranking — a second-stage pass over vector-search candidates. When
    # disabled, retrieval behaves exactly as before (vector search only).
    # reranker_provider selects the implementation when enabled:
    #   "lexical"       - no extra dependency, blends vector similarity with
    #                     query/chunk token overlap (the original milestone 8)
    #   "cross_encoder" - a local sentence-transformers cross-encoder model;
    #                     more accurate, but adds a PyTorch dependency and a
    #                     one-time model download
    rerank_enabled: bool = False
    reranker_provider: str = "lexical"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_candidate_count: int = 20
    rerank_top_k: int = 5

    # Agent — bounds the number of sequential tool-calling rounds AgentService
    # will run before it is forced to produce a final answer from whatever
    # tool results it has gathered so far, regardless of what the model
    # keeps asking for.
    agent_max_iterations: int = 5

    # Hybrid search — fuses vector similarity with PostgreSQL full-text (keyword)
    # search via Reciprocal Rank Fusion, so an exact technical term a pure
    # embedding match might miss (e.g. an error code) still surfaces. Disabled
    # by default: off means byte-for-byte the same retrieval behavior as before.
    hybrid_search_enabled: bool = False

    # Uploads
    max_upload_size_mb: int = 20
    upload_directory: str = "uploads"

    # Authentication
    jwt_secret_key: str = "insecure-development-secret-change-me"
    jwt_algorithm: str = "HS256"
    # Short-lived by design — long-lived sessions are handled by the
    # server-side, rotating refresh session below, not by a long-lived
    # access token itself.
    access_token_expire_minutes: int = 15

    # Server-side refresh sessions (see app/services/refresh_session_service.py).
    # The raw refresh token is only ever handed to the browser as an HttpOnly
    # cookie — never stored in the database (only its hash) or read by JS.
    refresh_token_expire_days: int = 30
    refresh_cookie_name: str = "masteacon_refresh_token"
    # Must be True whenever served over HTTPS (i.e. always in production) so
    # the cookie is never sent over plain HTTP. Set to False only for local
    # HTTP development.
    refresh_cookie_secure: bool = True
    # "lax" blocks the cookie from being sent on cross-site POST/fetch
    # requests (the actual CSRF-relevant case for /auth/refresh, /auth/logout,
    # /auth/logout-all) while still working for normal top-level navigation -
    # see the Security Notes in README.md for the full CSRF reasoning.
    refresh_cookie_samesite: str = "lax"

    # Password reset tokens (see app/services/password_reset_service.py).
    password_reset_ttl_minutes: int = 30

    # Public authentication abuse protection
    auth_rate_limit_enabled: bool = True
    auth_register_rate_limit: int = 5
    auth_register_rate_window_seconds: int = 900
    auth_login_rate_limit: int = 10
    auth_login_rate_window_seconds: int = 300

    # Number of trusted reverse-proxy hops that append to X-Forwarded-For
    # before a request reaches this app — see app/core/client_ip.py. 0 (the
    # safe default) means X-Forwarded-For is ignored entirely and the direct
    # socket peer is used; this deployment's production chain
    # (Client -> Caddy -> nginx -> Uvicorn) is exactly 1.
    trusted_proxy_count: int = 0

    # Cloudflare Turnstile
    turnstile_enabled: bool = False
    turnstile_secret_key: str = ""

    # Email verification
    email_verification_ttl_minutes: int = 30

    # Verification email delivery — via the Resend transactional email API
    # (https://resend.com), a single authenticated HTTPS call, no SMTP/app
    # passwords involved.
    email_delivery_enabled: bool = False
    resend_api_key: str = ""
    email_from_address: str = ""
    frontend_base_url: str = "http://localhost:5173"

    # Conversation history — bounds how much prior chat context is fed back into
    # the RAG prompt, so a long-running conversation can't grow the prompt without limit.
    conversation_history_max_messages: int = 10
    conversation_history_max_tokens: int = 2000

    # Frontend origins allowed to call this API (comma-separated). Includes
    # both `localhost` and `127.0.0.1` variants by default — browsers treat
    # them as different origins for CORS even though they're the same
    # machine, and it's easy to end up on one or the other (a bookmark, a
    # tool that opens 127.0.0.1, Docker Desktop's own printed URL, ...),
    # which otherwise surfaces as an opaque "Failed to fetch" in the UI with
    # a CORS error visible only in the browser console.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the environment is parsed only once."""
    return Settings()
