"""Deterministic fake providers/repositories used across the test suite.

These avoid any real network calls to OpenAI and avoid requiring a live
PostgreSQL/pgvector instance for unit tests.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole
from app.models.user import User
from app.models.workspace import Workspace
from app.providers.base_chat_provider import ChatProvider, ToolCallDecision
from app.providers.base_embedding_provider import EmbeddingProvider
from app.services.document_indexing_service import DocumentIndexingService
from app.services.indexing_dispatcher import IndexingDispatcher
from app.services.reciprocal_rank_fusion import reciprocal_rank_fusion_scores


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider: hashes text into a fixed-size vector."""

    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    async def embed_text(self, text: str) -> list[float]:
        return self._vectorize(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    def _vectorize(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text) or 1
        return [((seed * (i + 1)) % 97) / 97 for i in range(self.dimensions)]


class FakeChatProvider(ChatProvider):
    """Chat provider that echoes back a canned answer for assertions."""

    def __init__(
        self,
        answer: str = "This is a fake answer based on the given context.",
        tool_decision: ToolCallDecision | None = None,
        tool_decisions: list[ToolCallDecision] | None = None,
        raise_on_complete: Exception | None = None,
    ) -> None:
        self.answer = answer
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None
        self.user_prompts: list[str] = []
        self._tool_decision = tool_decision
        # A queue of decisions to return across successive decide_tool_calls()
        # calls — for testing a multi-round agent loop. The last entry repeats
        # once exhausted, so a test doesn't have to predict the exact round count.
        self._tool_decisions = list(tool_decisions) if tool_decisions is not None else None
        self._decision_call_count = 0
        self._raise_on_complete = raise_on_complete

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.user_prompts.append(user_prompt)
        if self._raise_on_complete is not None:
            raise self._raise_on_complete
        return self.answer

    async def decide_tool_calls(self, system_prompt, user_prompt, tools) -> ToolCallDecision:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.user_prompts.append(user_prompt)
        if self._tool_decisions is not None:
            index = min(self._decision_call_count, len(self._tool_decisions) - 1)
            self._decision_call_count += 1
            return self._tool_decisions[index]
        if self._tool_decision is not None:
            return self._tool_decision
        return ToolCallDecision(text=self.answer, tool_calls=[])


@dataclass
class FakeChunkRow:
    document_id: int
    filename: str
    chunk_index: int
    content: str
    similarity_score: float
    workspace_id: int = 1
    content_type: str = "text/plain"
    # A stand-in chunk id, distinct from document_id, so hybrid_search's RRF
    # fusion (which dedups by chunk id) behaves like it would against real
    # DocumentChunk rows. Defaults to chunk_index, which is unique enough for
    # the small fixture lists these tests build.
    id: int | None = None
    # Simulated PostgreSQL ts_rank score for keyword_search — 0 means "this
    # row is not a keyword match" (real ts_rank is 0 for no match too).
    keyword_rank_score: float = 0.0

    def __post_init__(self) -> None:
        if self.id is None:
            self.id = self.chunk_index


class _FakeDoc:
    def __init__(self, filename: str) -> None:
        self.filename = filename


class _FakeChunk:
    def __init__(self, row: FakeChunkRow) -> None:
        self.id = row.id
        self.document_id = row.document_id
        self.chunk_index = row.chunk_index
        self.content = row.content
        self.document = _FakeDoc(row.filename)


class FakeChunkRepository:
    """In-memory stand-in for ChunkRepository, used to test RetrievalService."""

    def __init__(self, rows: list[FakeChunkRow] | None = None) -> None:
        self._rows = rows if rows is not None else []

    async def similarity_search(
        self,
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
        workspace_id: int,
        document_id: int | None = None,
        content_type: str | None = None,
    ):
        matches = [
            row
            for row in self._rows
            if row.similarity_score >= similarity_threshold
            and row.workspace_id == workspace_id
            and (document_id is None or row.document_id == document_id)
            and (content_type is None or row.content_type == content_type)
        ]
        matches.sort(key=lambda r: r.similarity_score, reverse=True)

        return [(_FakeChunk(row), row.similarity_score) for row in matches[:limit]]

    async def keyword_search(
        self,
        query_text: str,
        limit: int,
        workspace_id: int,
        document_id: int | None = None,
        content_type: str | None = None,
    ):
        matches = [
            row
            for row in self._rows
            if row.keyword_rank_score > 0
            and row.workspace_id == workspace_id
            and (document_id is None or row.document_id == document_id)
            and (content_type is None or row.content_type == content_type)
        ]
        matches.sort(key=lambda r: r.keyword_rank_score, reverse=True)
        return [(_FakeChunk(row), row.keyword_rank_score) for row in matches[:limit]]

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
        workspace_id: int,
        document_id: int | None = None,
        content_type: str | None = None,
        candidate_count: int | None = None,
        rrf_k: int = 60,
    ):
        fetch_limit = candidate_count or limit
        vector_matches = await self.similarity_search(
            query_embedding, fetch_limit, similarity_threshold, workspace_id, document_id, content_type
        )
        keyword_matches = await self.keyword_search(query_text, fetch_limit, workspace_id, document_id, content_type)

        fused_scores = reciprocal_rank_fusion_scores(
            [
                [chunk.id for chunk, _ in vector_matches],
                [chunk.id for chunk, _ in keyword_matches],
            ],
            rrf_k=rrf_k,
        )

        chunks_by_id = {chunk.id: chunk for chunk, _ in vector_matches}
        similarity_by_id = {chunk.id: similarity for chunk, similarity in vector_matches}
        for chunk, _keyword_rank in keyword_matches:
            chunks_by_id.setdefault(chunk.id, chunk)
            similarity_by_id.setdefault(chunk.id, 0.0)

        ordered_ids = sorted(fused_scores, key=lambda chunk_id: fused_scores[chunk_id], reverse=True)[:limit]
        return [(chunks_by_id[chunk_id], similarity_by_id[chunk_id]) for chunk_id in ordered_ids]

    async def delete_by_document_id(self, document_id: int) -> None:
        self._rows = [r for r in self._rows if r.document_id != document_id]

    async def bulk_create(self, chunks: list) -> list:
        self.created_chunks = chunks
        return chunks

    async def count_by_document_id(self, document_id: int) -> int:
        created = getattr(self, "created_chunks", [])
        return len([c for c in created if getattr(c, "document_id", None) == document_id])

    async def commit(self) -> None:
        pass


class FakeUserRepository:
    """In-memory stand-in for UserRepository, used to test AuthService."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._next_id = 1

    async def create(self, email: str, password_hash: str) -> User:
        now = datetime.now(timezone.utc)
        user = User(email=email, password_hash=password_hash, is_active=True)
        user.id = self._next_id
        user.created_at = now
        user.updated_at = now
        self._next_id += 1
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def set_email_verification(
        self,
        user: User,
        token_hash: str,
        expires_at: datetime,
    ) -> User:
        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = expires_at
        user.is_email_verified = False
        user.email_verified_at = None
        return user

    async def get_by_verification_token_hash(
        self,
        token_hash: str,
    ) -> User | None:
        for user in self._users.values():
            if user.email_verification_token_hash == token_hash:
                return user
        return None

    async def mark_email_verified(
        self,
        user: User,
        verified_at: datetime,
    ) -> User:
        user.is_email_verified = True
        user.email_verified_at = verified_at
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None
        return user

    async def update_password(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        return user

    async def commit(self) -> None:
        pass


class FakeDocumentRepository:
    """In-memory stand-in for DocumentRepository, used to test DocumentService."""

    def __init__(self) -> None:
        self._documents: dict[int, Document] = {}
        self._next_id = 1

    async def create(
        self, filename: str, stored_filename: str, content_type: str, workspace_id: int
    ) -> Document:
        now = datetime.now(timezone.utc)
        document = Document(
            filename=filename,
            stored_filename=stored_filename,
            content_type=content_type,
            status=DocumentStatus.UPLOADED,
            workspace_id=workspace_id,
        )
        document.id = self._next_id
        document.chunks = []
        document.created_at = now
        document.updated_at = now
        self._next_id += 1
        self._documents[document.id] = document
        return document

    async def get_by_id(self, document_id: int) -> Document | None:
        return self._documents.get(document_id)

    async def get_by_id_and_workspace(self, document_id: int, workspace_id: int) -> Document | None:
        document = self._documents.get(document_id)
        if document is not None and document.workspace_id == workspace_id:
            return document
        return None

    async def list_by_workspace(self, workspace_id: int) -> list[Document]:
        return [d for d in self._documents.values() if d.workspace_id == workspace_id]

    async def update_status(
        self, document: Document, status: DocumentStatus, error_message: str | None = None
    ) -> Document:
        document.status = status
        document.error_message = error_message
        document.updated_at = datetime.now(timezone.utc)
        return document

    async def commit(self) -> None:
        pass


class FakeIndexingDispatcher(IndexingDispatcher):
    """Test IndexingDispatcher: runs indexing inline (synchronously) via the given
    DocumentIndexingService, instead of enqueueing a real Celery task.

    Built against the *same* fake repositories as the DocumentService under test,
    so by the time `dispatch()` returns, the document has already moved through
    processing -> indexed|failed — preserving the old, deterministic, synchronous
    test behavior without touching Celery or a real broker.
    """

    def __init__(self, indexing_service: DocumentIndexingService) -> None:
        self._indexing_service = indexing_service
        self.dispatched_ids: list[int] = []

    async def dispatch(self, document_id: int) -> None:
        self.dispatched_ids.append(document_id)
        await self._indexing_service.index(document_id)


class FakeWorkspaceRepository:
    """In-memory stand-in for WorkspaceRepository, used to test WorkspaceService."""

    def __init__(self) -> None:
        self._workspaces: dict[int, Workspace] = {}
        self._next_id = 1

    async def create(self, name: str, owner_id: int) -> Workspace:
        now = datetime.now(timezone.utc)
        workspace = Workspace(name=name, owner_id=owner_id)
        workspace.id = self._next_id
        workspace.created_at = now
        workspace.updated_at = now
        self._next_id += 1
        self._workspaces[workspace.id] = workspace
        return workspace

    async def get_by_id(self, workspace_id: int) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    async def list_by_owner(self, owner_id: int) -> list[Workspace]:
        return [w for w in self._workspaces.values() if w.owner_id == owner_id]

    async def commit(self) -> None:
        pass


class FakeConversationRepository:
    """In-memory stand-in for ConversationRepository, used to test ConversationService."""

    def __init__(self) -> None:
        self._conversations: dict[int, Conversation] = {}
        self._next_id = 1

    async def create(self, workspace_id: int, user_id: int, title: str) -> Conversation:
        now = datetime.now(timezone.utc)
        conversation = Conversation(workspace_id=workspace_id, user_id=user_id, title=title)
        conversation.id = self._next_id
        conversation.created_at = now
        conversation.updated_at = now
        self._next_id += 1
        self._conversations[conversation.id] = conversation
        return conversation

    async def get_by_id_and_owner(self, conversation_id: int, user_id: int) -> Conversation | None:
        conversation = self._conversations.get(conversation_id)
        if conversation is not None and conversation.user_id == user_id:
            return conversation
        return None

    async def list_by_workspace_and_owner(self, workspace_id: int, user_id: int) -> list[Conversation]:
        return [
            c
            for c in self._conversations.values()
            if c.workspace_id == workspace_id and c.user_id == user_id
        ]

    async def commit(self) -> None:
        pass


class FakeMessageRepository:
    """In-memory stand-in for MessageRepository, used to test ConversationService."""

    def __init__(self) -> None:
        self._messages: dict[int, Message] = {}
        self._next_id = 1

    async def create(self, conversation_id: int, role: MessageRole, content: str) -> Message:
        now = datetime.now(timezone.utc)
        message = Message(conversation_id=conversation_id, role=role, content=content)
        message.id = self._next_id
        message.created_at = now
        self._next_id += 1
        self._messages[message.id] = message
        return message

    async def list_by_conversation(self, conversation_id: int) -> list[Message]:
        return [m for m in self._messages.values() if m.conversation_id == conversation_id]

    async def list_recent_by_conversation(self, conversation_id: int, limit: int) -> list[Message]:
        matches = [m for m in self._messages.values() if m.conversation_id == conversation_id]
        return matches[-limit:]

    async def commit(self) -> None:
        pass


class FakeAuthProtectionService:
    """Deterministic auth-protection fake used by route tests."""

    def __init__(self) -> None:
        self.blocked_actions: set[str] = set()
        self.retry_after = 60
        self.checks: list[tuple[str, str]] = []
        self.resets: list[tuple[str, str]] = []

    @staticmethod
    def is_honeypot_triggered(value: str | None) -> bool:
        return bool(value and value.strip())

    async def check_rate_limit(
        self,
        action: str,
        identifier: str,
    ):
        from app.services.auth_protection_service import RateLimitResult

        self.checks.append((action, identifier))

        if action in self.blocked_actions:
            return RateLimitResult(
                allowed=False,
                retry_after=self.retry_after,
            )

        return RateLimitResult(allowed=True)

    async def reset_rate_limit(
        self,
        action: str,
        identifier: str,
    ) -> None:
        self.resets.append((action, identifier))


class FakeTurnstileService:
    """Deterministic Turnstile fake used by authentication route tests."""

    def __init__(self) -> None:
        self.success = True
        self.calls: list[tuple[str, str | None]] = []

    async def verify(
        self,
        *,
        token: str,
        remote_ip: str | None = None,
    ):
        from app.services.turnstile_service import TurnstileVerificationResult

        self.calls.append((token, remote_ip))

        return TurnstileVerificationResult(
            success=self.success,
            action="register" if self.success else None,
        )


class FakeObservabilityEvent:
    """Attribute-access record shape matching the real ObservabilityEvent model,
    for FakeObservabilityEventRepository.list_by_user() results."""

    def __init__(self, **kwargs) -> None:
        self.created_at = kwargs.pop("created_at", None) or datetime.now(timezone.utc)
        self.__dict__.update(kwargs)


class FakeObservabilityEventRepository:
    """In-memory stand-in for ObservabilityEventRepository."""

    def __init__(self) -> None:
        self.created: list[FakeObservabilityEvent] = []

    async def create(self, **kwargs) -> FakeObservabilityEvent:
        event = FakeObservabilityEvent(**kwargs)
        self.created.append(event)
        return event

    async def list_by_user(self, user_id: int, since: datetime) -> list[FakeObservabilityEvent]:
        return [event for event in self.created if event.user_id == user_id and event.created_at >= since]


class _FakeHashedTokenRow:
    """Shared attribute-access row shape for the two fakes below."""

    def __init__(self, id: int, user_id: int, token_hash: str, expires_at: datetime, **extra) -> None:
        self.id = id
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at
        for key, value in extra.items():
            setattr(self, key, value)


class FakeRefreshSessionRepository:
    """In-memory stand-in for RefreshSessionRepository."""

    def __init__(self) -> None:
        self._rows: dict[int, _FakeHashedTokenRow] = {}
        self._next_id = 1

    async def create(self, user_id: int, token_hash: str, expires_at: datetime):
        row = _FakeHashedTokenRow(
            id=self._next_id, user_id=user_id, token_hash=token_hash, expires_at=expires_at,
            revoked_at=None, replaced_by_id=None,
        )
        self._rows[row.id] = row
        self._next_id += 1
        return row

    async def get_by_token_hash(self, token_hash: str):
        for row in self._rows.values():
            if row.token_hash == token_hash:
                return row
        return None

    async def revoke(self, refresh_session, revoked_at: datetime, replaced_by_id: int | None = None) -> None:
        refresh_session.revoked_at = revoked_at
        if replaced_by_id is not None:
            refresh_session.replaced_by_id = replaced_by_id

    async def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> None:
        for row in self._rows.values():
            if row.user_id == user_id and row.revoked_at is None:
                row.revoked_at = revoked_at

    async def commit(self) -> None:
        pass


class FakePasswordResetTokenRepository:
    """In-memory stand-in for PasswordResetTokenRepository."""

    def __init__(self) -> None:
        self._rows: dict[int, _FakeHashedTokenRow] = {}
        self._next_id = 1

    async def create(self, user_id: int, token_hash: str, expires_at: datetime):
        row = _FakeHashedTokenRow(
            id=self._next_id, user_id=user_id, token_hash=token_hash, expires_at=expires_at, used_at=None
        )
        self._rows[row.id] = row
        self._next_id += 1
        return row

    async def get_by_token_hash(self, token_hash: str):
        for row in self._rows.values():
            if row.token_hash == token_hash:
                return row
        return None

    async def mark_used(self, reset_token, used_at: datetime) -> None:
        reset_token.used_at = used_at

    async def commit(self) -> None:
        pass
