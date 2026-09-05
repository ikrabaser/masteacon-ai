"""FastAPI dependency providers wiring repositories, services and providers together."""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.exceptions import AppError, InvalidCredentialsError
from app.core.security import decode_access_token
from app.models.user import User
from app.providers.base_chat_provider import ChatProvider
from app.providers.base_embedding_provider import EmbeddingProvider
from app.providers.chat_provider_factory import create_chat_provider
from app.providers.openai_provider import OpenAIEmbeddingProvider
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.observability_event_repository import ObservabilityEventRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_session_repository import RefreshSessionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.auth_protection_service import AuthProtectionService
from app.services.turnstile_service import TurnstileService
from app.services.conversation_service import ConversationService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.email_verification_service import EmailVerificationService
from app.services.email_service import EmailService
from app.services.password_reset_service import PasswordResetService
from app.services.refresh_session_service import RefreshSessionService
from app.services.agent_service import AgentService
from app.services.cross_encoder_reranking_service import CrossEncoderRerankingService
from app.services.indexing_dispatcher import IndexingDispatcher
from app.services.observability_service import ObservabilityService
from app.evaluation.generation_evaluator import GenerationEvaluator
from app.services.query_rewriting_service import QueryRewritingService
from app.services.rag_service import GroundednessChecker, RagService
from app.services.reranking_service import RerankingService
from app.services.retrieval_service import RetrievalService
from app.services.retrieval_types import QueryRewriter, Reranker
from app.services.tool_execution_service import ToolExecutionService
from app.services.workspace_service import WorkspaceService
from app.tasks.document_indexing_task import CeleryIndexingDispatcher
from app.tools.get_document_tool import GetDocumentTool
from app.tools.list_documents_tool import ListDocumentsTool
from app.tools.list_workspaces_tool import ListWorkspacesTool
from app.tools.registry import ToolRegistry
from app.tools.search_knowledge_tool import SearchKnowledgeTool
from app.tools.summarize_document_tool import SummarizeDocumentTool
from app.tools.workspace_stats_tool import WorkspaceStatsTool

_bearer_scheme = HTTPBearer(auto_error=False)


def get_embedding_provider(settings: Settings = Depends(get_settings)) -> EmbeddingProvider:
    return OpenAIEmbeddingProvider(api_key=settings.openai_api_key, model=settings.openai_embedding_model)


def get_chat_provider(settings: Settings = Depends(get_settings)) -> ChatProvider:
    """Return the configured ChatProvider — OpenAI or Anthropic, per LLM_PROVIDER."""
    return create_chat_provider(settings)


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_email_service(
    settings: Settings = Depends(get_settings),
) -> EmailService:
    return EmailService(settings=settings)


def get_email_verification_service(
    settings: Settings = Depends(get_settings),
) -> EmailVerificationService:
    return EmailVerificationService(
        ttl_minutes=settings.email_verification_ttl_minutes,
    )


def get_auth_service(
    settings: Settings = Depends(get_settings),
    user_repository: UserRepository = Depends(get_user_repository),
    email_verification_service: EmailVerificationService = Depends(
        get_email_verification_service
    ),
    email_service: EmailService = Depends(get_email_service),
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        settings=settings,
        email_verification_service=email_verification_service,
        email_service=email_service,
    )


def get_refresh_session_repository(session: AsyncSession = Depends(get_db)) -> RefreshSessionRepository:
    return RefreshSessionRepository(session)


def get_refresh_session_service(
    settings: Settings = Depends(get_settings),
    repository: RefreshSessionRepository = Depends(get_refresh_session_repository),
) -> RefreshSessionService:
    return RefreshSessionService(repository, ttl_days=settings.refresh_token_expire_days)


def get_password_reset_token_repository(
    session: AsyncSession = Depends(get_db),
) -> PasswordResetTokenRepository:
    return PasswordResetTokenRepository(session)


def get_password_reset_service(
    settings: Settings = Depends(get_settings),
    user_repository: UserRepository = Depends(get_user_repository),
    reset_token_repository: PasswordResetTokenRepository = Depends(get_password_reset_token_repository),
    refresh_session_service: RefreshSessionService = Depends(get_refresh_session_service),
    email_service: EmailService = Depends(get_email_service),
) -> PasswordResetService:
    return PasswordResetService(
        user_repository=user_repository,
        reset_token_repository=reset_token_repository,
        refresh_session_service=refresh_session_service,
        email_service=email_service,
        ttl_minutes=settings.password_reset_ttl_minutes,
    )


def get_auth_protection_service(
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
) -> AuthProtectionService:
    return AuthProtectionService(
        redis_client=redis_client,
        settings=settings,
    )


def get_turnstile_service(
    settings: Settings = Depends(get_settings),
) -> TurnstileService:
    return TurnstileService(settings=settings)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    """Resolve the authenticated user from a Bearer JWT, or raise 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    try:
        subject = decode_access_token(credentials.credentials, settings)
        user_id = int(subject)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise InvalidCredentialsError("Invalid or expired authentication token.") from exc

    user = await user_repository.get_by_id(user_id)
    if user is None or not user.is_active:
        raise InvalidCredentialsError("Invalid or expired authentication token.")
    return user


def get_workspace_repository(session: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_workspace_service(
    workspace_repository: WorkspaceRepository = Depends(get_workspace_repository),
) -> WorkspaceService:
    return WorkspaceService(workspace_repository)


def get_document_repository(session: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(session)


def get_chunk_repository(session: AsyncSession = Depends(get_db)) -> ChunkRepository:
    return ChunkRepository(session)


def get_embedding_service(
    provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> EmbeddingService:
    return EmbeddingService(provider)


def get_indexing_dispatcher() -> IndexingDispatcher:
    """Production dispatcher: enqueues indexing onto the Celery/Redis queue."""
    return CeleryIndexingDispatcher()


def get_document_service(
    settings: Settings = Depends(get_settings),
    document_repository: DocumentRepository = Depends(get_document_repository),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
    indexing_dispatcher: IndexingDispatcher = Depends(get_indexing_dispatcher),
) -> DocumentService:
    return DocumentService(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        indexing_dispatcher=indexing_dispatcher,
        upload_directory=settings.upload_directory,
        max_upload_size_mb=settings.max_upload_size_mb,
    )


class UnsupportedRerankerProviderError(AppError):
    """Raised when RERANKER_PROVIDER is set to an unrecognized value."""

    status_code = 500


def get_reranking_service(settings: Settings = Depends(get_settings)) -> Reranker | None:
    """Return the configured Reranker only when reranking is enabled — keeps
    the "disabled means unchanged vector-search behavior" contract explicit
    here. `RERANK_ENABLED=false` (the default) never even imports the
    cross-encoder implementation, so a plain install never needs PyTorch.
    """
    if not settings.rerank_enabled:
        return None

    provider = settings.reranker_provider.strip().lower()
    if provider == "lexical":
        return RerankingService()
    if provider == "cross_encoder":
        return CrossEncoderRerankingService(model_name=settings.cross_encoder_model)

    raise UnsupportedRerankerProviderError(
        f"Unsupported RERANKER_PROVIDER '{settings.reranker_provider}'. Supported: lexical, cross_encoder."
    )


def get_query_rewriting_service(settings: Settings = Depends(get_settings)) -> QueryRewriter | None:
    """Return a QueryRewritingService only when query rewriting is enabled —
    same "disabled means unchanged behavior" contract as reranking/hybrid search.

    Deliberately does NOT take `chat_provider: ChatProvider = Depends(get_chat_provider)`
    as a parameter: FastAPI resolves every declared `Depends()` unconditionally,
    even ones the function body never ends up using — that would construct a
    real ChatOpenAI/ChatAnthropic client (and fail without an API key) on every
    request that reaches RetrievalService, regardless of whether query
    rewriting is even enabled. Calling create_chat_provider() directly here,
    only inside the `if`, keeps construction genuinely conditional.
    """
    if not settings.query_rewriting_enabled:
        return None
    return QueryRewritingService(create_chat_provider(settings))


def get_retrieval_service(
    settings: Settings = Depends(get_settings),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    reranking_service: Reranker | None = Depends(get_reranking_service),
    query_rewriting_service: QueryRewriter | None = Depends(get_query_rewriting_service),
) -> RetrievalService:
    return RetrievalService(
        chunk_repository=chunk_repository,
        embedding_service=embedding_service,
        default_top_k=settings.search_top_k,
        similarity_threshold=settings.similarity_threshold,
        reranking_service=reranking_service,
        candidate_count=settings.retrieval_candidate_count,
        rerank_top_k=settings.rerank_top_k,
        hybrid_search_enabled=settings.hybrid_search_enabled,
        query_rewriting_service=query_rewriting_service,
    )


def get_groundedness_checker(settings: Settings = Depends(get_settings)) -> GroundednessChecker | None:
    """Return a GenerationEvaluator (as a GroundednessChecker) only when the
    live groundedness check is enabled — same "disabled means unchanged
    behavior" contract, and same reason `get_query_rewriting_service` calls
    create_chat_provider() directly here instead of taking it as a Depends()
    parameter: constructing a real ChatProvider must stay genuinely
    conditional, not something FastAPI resolves on every request regardless.
    """
    if not settings.groundedness_check_enabled:
        return None
    return GenerationEvaluator(create_chat_provider(settings))


def get_observability_event_repository(session: AsyncSession = Depends(get_db)) -> ObservabilityEventRepository:
    return ObservabilityEventRepository(session)


def get_observability_service(
    repository: ObservabilityEventRepository = Depends(get_observability_event_repository),
) -> ObservabilityService:
    return ObservabilityService(repository)


def get_rag_service(
    settings: Settings = Depends(get_settings),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_provider: ChatProvider = Depends(get_chat_provider),
    groundedness_checker: GroundednessChecker | None = Depends(get_groundedness_checker),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> RagService:
    return RagService(
        retrieval_service=retrieval_service,
        chat_provider=chat_provider,
        groundedness_checker=groundedness_checker,
        groundedness_threshold=settings.groundedness_threshold,
        observability_recorder=observability_service,
    )


def get_conversation_repository(session: AsyncSession = Depends(get_db)) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(session: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(session)


def get_conversation_service(
    settings: Settings = Depends(get_settings),
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    message_repository: MessageRepository = Depends(get_message_repository),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    rag_service: RagService = Depends(get_rag_service),
) -> ConversationService:
    return ConversationService(
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        workspace_service=workspace_service,
        rag_service=rag_service,
        history_max_messages=settings.conversation_history_max_messages,
        history_max_tokens=settings.conversation_history_max_tokens,
    )


def get_tool_registry(
    document_service: DocumentService = Depends(get_document_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
    chat_provider: ChatProvider = Depends(get_chat_provider),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> ToolRegistry:
    return ToolRegistry(
        [
            ListWorkspacesTool(workspace_service),
            ListDocumentsTool(document_service, workspace_service),
            GetDocumentTool(document_service, workspace_service),
            SummarizeDocumentTool(document_service, workspace_service, chunk_repository, chat_provider),
            SearchKnowledgeTool(retrieval_service, workspace_service),
            WorkspaceStatsTool(document_service, workspace_service),
        ]
    )


def get_tool_execution_service(
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ToolExecutionService:
    return ToolExecutionService(tool_registry, observability_recorder=observability_service)


def get_agent_service(
    settings: Settings = Depends(get_settings),
    chat_provider: ChatProvider = Depends(get_chat_provider),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    tool_execution_service: ToolExecutionService = Depends(get_tool_execution_service),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> AgentService:
    return AgentService(
        chat_provider=chat_provider,
        tool_registry=tool_registry,
        tool_execution_service=tool_execution_service,
        max_iterations=settings.agent_max_iterations,
        observability_recorder=observability_service,
    )
