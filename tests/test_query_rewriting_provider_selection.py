"""Tests for get_query_rewriting_service — in particular, that it never
constructs a real ChatProvider when disabled.

Regression test: an earlier version of this dependency declared
`chat_provider: ChatProvider = Depends(get_chat_provider)` as a parameter,
which FastAPI resolves unconditionally regardless of whether the function
body ends up using it — constructing a real ChatOpenAI/ChatAnthropic client
(and failing without an API key configured) on every request that reaches
RetrievalService, even with QUERY_REWRITING_ENABLED=false. This broke
tests/test_workspace_isolation_routes.py in CI (no OPENAI_API_KEY there).
"""
from app.api.dependencies import get_query_rewriting_service
from app.core.config import Settings
from app.services.query_rewriting_service import QueryRewritingService


def test_returns_none_when_disabled_without_any_provider_credentials() -> None:
    # No OPENAI_API_KEY/ANTHROPIC_API_KEY at all — constructing a real
    # ChatProvider here would raise. It must not even be attempted.
    settings = Settings(query_rewriting_enabled=False, openai_api_key="", anthropic_api_key="")

    assert get_query_rewriting_service(settings) is None


def test_returns_a_query_rewriting_service_when_enabled() -> None:
    settings = Settings(query_rewriting_enabled=True, llm_provider="openai", openai_api_key="sk-test")

    service = get_query_rewriting_service(settings)

    assert isinstance(service, QueryRewritingService)
