"""Orchestrates the LLM function-calling pipeline as a bounded agent loop.

    LLM -> Tool Request -> Tool Registry -> Argument Validation -> Authorization Check
        -> Tool Execution -> Structured Result -> LLM (decide again, or answer) -> ... -> Final Answer

Each round, the model either answers directly or requests one or more tool
calls; every requested call is validated, authorization-checked and executed
through ToolExecutionService (never allowed to touch another user's data).
Results are folded back into the prompt and the model is asked again — so a
task that genuinely needs more than one lookup ("search for X, then use what
you found to check Y") can actually complete — for up to `max_iterations`
rounds. Two independent safety nets keep this from running away regardless of
what the model asks for: a hard round cap, and detection of the model asking
for the exact same tool call again (which would just waste a round without
new information) — either one forces an immediate final answer from whatever
was actually gathered.
"""
import json
import time

from app.core.logging import get_logger
from app.providers.base_chat_provider import ChatProvider
from app.services.tool_execution_service import ToolExecutionResult, ToolExecutionService
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)

DEFAULT_MAX_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are a knowledge assistant with access to a small set of read-only tools for "
    "inspecting and searching the user's own workspaces and documents. Use a tool only "
    "when it is needed to answer the question — and you may use more than one tool, one "
    "after another, if the task genuinely requires it (e.g. look something up, then use "
    "what you found to decide on a second lookup). Never invent tool results or "
    "workspace/document data you were not given. Once you have everything you need, "
    "answer directly instead of calling another tool."
)

FINAL_ANSWER_SYSTEM_PROMPT = (
    "You are a knowledge assistant. Answer the user's question using ONLY the tool "
    "results provided below. If a tool failed or returned nothing useful, say so "
    "plainly instead of guessing."
)


class AgentAskResponse:
    """Result of an agent turn: the final answer plus a log of every tool call made across the loop."""

    def __init__(self, answer: str, tool_calls: list[ToolExecutionResult]) -> None:
        self.answer = answer
        self.tool_calls = tool_calls


def _render_tool_results(results: list[ToolExecutionResult]) -> str:
    return "\n".join(
        f"- {r.name}: {'OK — ' + json.dumps(r.result) if r.success else 'FAILED — ' + (r.error or '')}"
        for r in results
    )


class AgentService:
    """Answers a question, letting the LLM call tools — possibly several, in sequence — as needed."""

    def __init__(
        self,
        chat_provider: ChatProvider,
        tool_registry: ToolRegistry,
        tool_execution_service: ToolExecutionService,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        self._chat_provider = chat_provider
        self._tool_registry = tool_registry
        self._tool_execution_service = tool_execution_service
        self._max_iterations = max_iterations

    async def ask(self, question: str, user_id: int) -> AgentAskResponse:
        total_started_at = time.perf_counter()
        question = question.strip()
        context = ToolContext(user_id=user_id)

        all_results: list[ToolExecutionResult] = []
        seen_calls: set[tuple[str, str]] = set()
        rounds_with_tool_calls = 0
        decision_duration_total_ms = 0.0
        stop_reason = "answered"

        for _round in range(self._max_iterations):
            prompt = (
                question
                if not all_results
                else (
                    f"Question: {question}\n\nTool results so far:\n{_render_tool_results(all_results)}\n\n"
                    "Call another tool if you still need more information, otherwise answer the question now."
                )
            )

            decision_started_at = time.perf_counter()
            decision = await self._chat_provider.decide_tool_calls(
                SYSTEM_PROMPT, prompt, self._tool_registry.specs()
            )
            decision_duration_total_ms += (time.perf_counter() - decision_started_at) * 1000

            if not decision.tool_calls:
                answer = (decision.text or "").strip()
                self._log(
                    user_id=user_id,
                    all_results=all_results,
                    rounds=rounds_with_tool_calls,
                    decision_duration_ms=decision_duration_total_ms,
                    generation_duration_ms=0.0,
                    total_started_at=total_started_at,
                    stop_reason=stop_reason,
                )
                return AgentAskResponse(answer=answer, tool_calls=all_results)

            round_results: list[ToolExecutionResult] = []
            made_a_new_call = False
            for call in decision.tool_calls:
                call_key = (call.name, json.dumps(call.arguments, sort_keys=True))
                if call_key in seen_calls:
                    # The model is asking for the exact same call again — executing
                    # it again would just waste a round without new information.
                    continue
                seen_calls.add(call_key)
                made_a_new_call = True
                round_results.append(await self._tool_execution_service.execute(call.id, call.name, call.arguments, context))

            all_results.extend(round_results)
            if round_results:
                rounds_with_tool_calls += 1

            if not made_a_new_call:
                stop_reason = "repeated_call"
                break
        else:
            stop_reason = "max_iterations"

        # Either the loop hit its bound, or the model kept repeating an
        # already-executed call — force a final answer from whatever tool
        # results were actually gathered, rather than looping forever or
        # returning nothing.
        follow_up_prompt = f"Question: {question}\n\nTool results:\n{_render_tool_results(all_results)}\n\nAnswer:"
        generation_started_at = time.perf_counter()
        answer = await self._chat_provider.complete(FINAL_ANSWER_SYSTEM_PROMPT, follow_up_prompt)
        generation_duration_ms = (time.perf_counter() - generation_started_at) * 1000

        self._log(
            user_id=user_id,
            all_results=all_results,
            rounds=rounds_with_tool_calls,
            decision_duration_ms=decision_duration_total_ms,
            generation_duration_ms=generation_duration_ms,
            total_started_at=total_started_at,
            stop_reason=stop_reason,
        )
        return AgentAskResponse(answer=answer.strip(), tool_calls=all_results)

    def _log(
        self,
        *,
        user_id: int,
        all_results: list[ToolExecutionResult],
        rounds: int,
        decision_duration_ms: float,
        generation_duration_ms: float,
        total_started_at: float,
        stop_reason: str,
    ) -> None:
        logger.info(
            "Agent request completed" if all_results else "Agent request completed without calling any tool",
            extra={
                "event": "agent_request",
                "user_id": user_id,
                "provider": self._chat_provider.provider_name,
                "model": self._chat_provider.model,
                "rounds": rounds,
                "tool_call_count": len(all_results),
                "tool_names": [r.name for r in all_results],
                "decision_duration_ms": round(decision_duration_ms, 2),
                "generation_duration_ms": round(generation_duration_ms, 2),
                "total_duration_ms": round((time.perf_counter() - total_started_at) * 1000, 2),
                "success": all(r.success for r in all_results) if all_results else True,
                "stop_reason": stop_reason,
            },
        )
