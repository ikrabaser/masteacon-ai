"""RAG question-answering endpoint — scoped to a workspace owned by the caller."""
from fastapi import APIRouter, Depends

from app.api.dependencies import (
    enforce_ask_usage_limit,
    enforce_workspace_ask_usage_limit,
    get_current_user,
    get_rag_service,
    get_settings,
    get_usage_guard_service,
    get_workspace_service,
)
from app.core.config import Settings
from app.models.user import User
from app.schemas.rag import AskRequest, AskResponse
from app.services.rag_service import RagService
from app.services.usage_guard_service import UsageGuardService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/v1", tags=["rag"])


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    rag_service: RagService = Depends(get_rag_service),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    usage_guard: UsageGuardService = Depends(get_usage_guard_service),
    settings: Settings = Depends(get_settings),
    _usage_limit: None = Depends(enforce_ask_usage_limit),
) -> AskResponse:
    """Answer a natural-language question using retrieval-augmented generation."""
    await workspace_service.get_owned_workspace(request.workspace_id, current_user.id)
    # A shared cap across every user in this workspace, on top of the
    # per-user limit already enforced by enforce_ask_usage_limit above.
    await enforce_workspace_ask_usage_limit(usage_guard, settings, request.workspace_id)

    return await rag_service.ask(request.question, workspace_id=request.workspace_id, user_id=current_user.id)
