"""Agent endpoint — LLM-controlled, tool-calling question answering."""
from fastapi import APIRouter, Depends

from app.api.dependencies import enforce_agent_usage_limit, get_agent_service, get_current_user
from app.models.user import User
from app.schemas.agent import AgentAskRequest, AgentAskResponse, ToolCallSummary
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/ask", response_model=AgentAskResponse)
async def agent_ask(
    request: AgentAskRequest,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    _usage_limit: None = Depends(enforce_agent_usage_limit),
) -> AgentAskResponse:
    """Ask a question; the LLM may call read-only tools scoped to the current user's own data."""
    response = await agent_service.ask(request.question, user_id=current_user.id)
    return AgentAskResponse(
        answer=response.answer,
        tool_calls=[
            ToolCallSummary(name=r.name, success=r.success, result=r.result, error=r.error)
            for r in response.tool_calls
        ],
    )
