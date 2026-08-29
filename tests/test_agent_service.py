"""Tests for AgentService: the tool-calling decision -> execution -> final-answer loop."""
import pytest

from app.providers.base_chat_provider import RequestedToolCall, ToolCallDecision
from app.services.agent_service import AgentService
from app.services.tool_execution_service import ToolExecutionService
from app.services.workspace_service import WorkspaceService
from app.tools.list_workspaces_tool import ListWorkspacesTool
from app.tools.registry import ToolRegistry
from tests.fakes import FakeChatProvider, FakeWorkspaceRepository

OWNER_ID = 1


async def _build_agent(tool_decision: ToolCallDecision | None, final_answer: str = "The final answer.") -> tuple[AgentService, FakeChatProvider]:
    workspace_repository = FakeWorkspaceRepository()
    workspace_service = WorkspaceService(workspace_repository)
    await workspace_service.create(name="My Workspace", owner_id=OWNER_ID)

    registry = ToolRegistry([ListWorkspacesTool(workspace_service)])
    chat_provider = FakeChatProvider(answer=final_answer, tool_decision=tool_decision)
    tool_execution_service = ToolExecutionService(registry)

    agent = AgentService(
        chat_provider=chat_provider, tool_registry=registry, tool_execution_service=tool_execution_service
    )
    return agent, chat_provider


@pytest.mark.asyncio
async def test_agent_answers_directly_when_no_tool_is_needed() -> None:
    agent, _ = await _build_agent(tool_decision=ToolCallDecision(text="Direct answer.", tool_calls=[]))

    response = await agent.ask("What is 2+2?", user_id=OWNER_ID)

    assert response.answer == "Direct answer."
    assert response.tool_calls == []


@pytest.mark.asyncio
async def test_agent_executes_a_requested_tool_and_synthesizes_a_final_answer() -> None:
    decision = ToolCallDecision(
        text=None, tool_calls=[RequestedToolCall(id="call-1", name="list_workspaces", arguments={})]
    )
    agent, chat_provider = await _build_agent(tool_decision=decision, final_answer="You have 1 workspace.")

    response = await agent.ask("What workspaces do I have?", user_id=OWNER_ID)

    assert response.answer == "You have 1 workspace."
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "list_workspaces"
    assert response.tool_calls[0].success is True
    assert response.tool_calls[0].result["workspaces"][0]["name"] == "My Workspace"
    # The tool result must have been folded into the follow-up prompt sent to the LLM.
    assert "My Workspace" in chat_provider.last_user_prompt


@pytest.mark.asyncio
async def test_agent_surfaces_a_failed_tool_call_without_crashing() -> None:
    decision = ToolCallDecision(
        text=None, tool_calls=[RequestedToolCall(id="call-1", name="not_a_real_tool", arguments={})]
    )
    agent, _ = await _build_agent(tool_decision=decision, final_answer="I could not find that information.")

    response = await agent.ask("Do something unsupported.", user_id=OWNER_ID)

    assert response.tool_calls[0].success is False
    assert response.answer == "I could not find that information."


@pytest.mark.asyncio
async def test_agent_asks_again_after_a_tool_call_and_can_answer_directly() -> None:
    """A genuine multi-round loop: the model calls a tool, is asked again with
    that tool's result folded in, and this time answers directly instead of
    the old single-round design's forced complete() call."""
    workspace_repository = FakeWorkspaceRepository()
    workspace_service = WorkspaceService(workspace_repository)
    await workspace_service.create(name="My Workspace", owner_id=OWNER_ID)

    registry = ToolRegistry([ListWorkspacesTool(workspace_service)])
    decisions = [
        ToolCallDecision(
            text=None, tool_calls=[RequestedToolCall(id="call-1", name="list_workspaces", arguments={})]
        ),
        ToolCallDecision(text="You have exactly one workspace: My Workspace.", tool_calls=[]),
    ]
    chat_provider = FakeChatProvider(tool_decisions=decisions)
    tool_execution_service = ToolExecutionService(registry)
    agent = AgentService(
        chat_provider=chat_provider, tool_registry=registry, tool_execution_service=tool_execution_service
    )

    response = await agent.ask("What workspaces do I have?", user_id=OWNER_ID)

    assert response.answer == "You have exactly one workspace: My Workspace."
    assert len(response.tool_calls) == 1
    # The second round's decision prompt must have seen the first round's tool result.
    assert "My Workspace" in chat_provider.user_prompts[1]


@pytest.mark.asyncio
async def test_agent_stops_at_max_iterations_and_forces_a_final_answer() -> None:
    """The model keeps asking for a *new*, distinct tool call every round —
    never repeating, never stopping on its own — so only the max_iterations
    bound should end this."""
    from pydantic import BaseModel

    from app.tools.base import BaseTool

    class _EchoArgs(BaseModel):
        index: int

    class _EchoTool(BaseTool):
        name = "echo"
        description = "Echoes back the given index."
        args_model = _EchoArgs

        async def execute(self, args: _EchoArgs, context) -> dict:
            return {"index": args.index}

    registry = ToolRegistry([_EchoTool()])
    decisions = [
        ToolCallDecision(
            text=None, tool_calls=[RequestedToolCall(id=f"call-{i}", name="echo", arguments={"index": i})]
        )
        for i in range(10)
    ]
    chat_provider = FakeChatProvider(tool_decisions=decisions, answer="Forced final answer.")
    tool_execution_service = ToolExecutionService(registry)
    agent = AgentService(
        chat_provider=chat_provider,
        tool_registry=registry,
        tool_execution_service=tool_execution_service,
        max_iterations=3,
    )

    response = await agent.ask("Keep going forever?", user_id=OWNER_ID)

    assert response.answer == "Forced final answer."
    # Bounded by max_iterations, not the 10 distinct calls the model kept asking for.
    assert len(response.tool_calls) == 3


class _RecordingObservabilityRecorder:
    """Captures record_event() calls for assertions, instead of writing to a DB."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def record_event(self, **kwargs) -> None:
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_agent_records_an_observability_event_per_turn_not_per_tool_call() -> None:
    decision = ToolCallDecision(
        text=None, tool_calls=[RequestedToolCall(id="call-1", name="list_workspaces", arguments={})]
    )
    workspace_repository = FakeWorkspaceRepository()
    workspace_service = WorkspaceService(workspace_repository)
    await workspace_service.create(name="My Workspace", owner_id=OWNER_ID)
    registry = ToolRegistry([ListWorkspacesTool(workspace_service)])
    chat_provider = FakeChatProvider(tool_decision=decision, answer="You have 1 workspace.")
    recorder = _RecordingObservabilityRecorder()
    agent = AgentService(
        chat_provider=chat_provider,
        tool_registry=registry,
        tool_execution_service=ToolExecutionService(registry),
        observability_recorder=recorder,
    )

    await agent.ask("What workspaces do I have?", user_id=OWNER_ID)

    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["event_type"] == "agent_request"
    assert call["user_id"] == OWNER_ID
    assert call["success"] is True
    assert call["extra"]["tool_call_count"] == 1
