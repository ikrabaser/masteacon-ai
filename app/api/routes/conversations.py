"""Conversation and message endpoints — persistent RAG chat history."""
from fastapi import APIRouter, Depends

from app.api.dependencies import enforce_conversation_usage_limit, get_conversation_service, get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreateRequest,
    MessageCreateResponse,
    MessageResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """Start a new conversation in a workspace owned by the current user."""
    conversation = await conversation_service.create_conversation(
        workspace_id=request.workspace_id, user_id=current_user.id, title=request.title
    )
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    """List the current user's conversations within a workspace they own."""
    conversations = await conversation_service.list_conversations(workspace_id, current_user.id)
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetailResponse:
    """Fetch a conversation and its full message history."""
    conversation = await conversation_service.get_conversation(conversation_id, current_user.id)
    messages = await conversation_service.get_messages(conversation.id)
    return ConversationDetailResponse(
        id=conversation.id,
        workspace_id=conversation.workspace_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.post("/{conversation_id}/messages", response_model=MessageCreateResponse, status_code=201)
async def post_message(
    conversation_id: int,
    request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    _usage_limit: None = Depends(enforce_conversation_usage_limit),
) -> MessageCreateResponse:
    """Ask a question in an existing conversation; runs the RAG pipeline with bounded history."""
    user_message, assistant_message, sources = await conversation_service.add_message(
        conversation_id=conversation_id, user_id=current_user.id, content=request.content
    )
    return MessageCreateResponse(
        user_message=MessageResponse.model_validate(user_message),
        assistant_message=MessageResponse.model_validate(assistant_message),
        sources=sources,
    )
