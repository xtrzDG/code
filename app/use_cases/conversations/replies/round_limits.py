"""
The limits of one reply's model rounds.

- At most `MAX_TOOL_CALLS_PER_RESPONSE` calls of one model response run; the
  others are answered with an error result the model can act on (every call
  still gets its result, as the providers require), so one response cannot
  fan out into dozens of bookings, requests or handoffs.
- Before every round after the first (the engine checked the first,
  `spend_brake`), the business's spend of its day is checked again: past
  its hard limit no further model call is made and the turn goes to the
  team, so a long tool loop cannot run past the limit.
- A call repeated too often in the turn does not run (`turn_budget`).
"""

from collections.abc import Sequence

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.assistant_tools import (
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.dto.spend_guard import SpendCheckRequest, SpendVerdict
from app.schemas.typings.assistants.constrained_integers import LlmToolCallLimit
from app.use_cases.conversations.replies.turn_budget import repeated_call_outcome
from app.use_cases.conversations.replies.turn_progress import (
    TurnProgress,
    record_tool_outcome,
)
from app.use_cases.conversations.tools.tool_outcomes import error_outcome

MAX_TOOL_CALLS_PER_RESPONSE: LlmToolCallLimit = LlmToolCallLimit(5)
TOO_MANY_TOOL_CALLS: str = (
    "Not run: one response may call at most {limit} tools. Call what is still "
    "needed in your next response, one step at a time."
)

type SpendCheck = UseCaseContract[SpendCheckRequest, SpendVerdict]


class SpendLimitReached(Exception):
    """The business passed its hard spend limit during the turn (technical)."""


def refused_call_outcome(
    call: LlmToolCall, limit: LlmToolCallLimit
) -> AssistantToolOutcome:
    """The error result of a call past the limit (it never ran)."""

    return error_outcome(call, TOO_MANY_TOOL_CALLS.format(limit=int(limit)))


def run_tool_calls(
    run_assistant_tool: UseCaseContract[AssistantToolInvocation, AssistantToolOutcome],
    turn: PreparedTurn,
    progress: TurnProgress,
    calls: Sequence[LlmToolCall],
    limit: LlmToolCallLimit,
) -> list[LlmToolResult]:
    """
    Every call's result, recorded in the turn's progress: those past the
    per-response limit and those repeated too often never ran.
    """

    results: list[LlmToolResult] = []
    repeated: bool = False
    for position, call in enumerate(calls):
        outcome: AssistantToolOutcome | None = None
        if position >= int(limit):
            outcome = refused_call_outcome(call, limit)
        else:
            outcome = repeated_call_outcome(progress, call)
            repeated = repeated or outcome is not None
        if outcome is None:
            outcome = run_assistant_tool.run(
                AssistantToolInvocation(context=turn.tool_context, call=call)
            )
        record_tool_outcome(progress, call, outcome)
        results.append(outcome.result)

    if repeated:
        progress.repeat_rounds += 1

    return results


def refuse_past_hard_limit(check: SpendCheck | None, turn: PreparedTurn) -> None:
    """
    Raises:
        SpendLimitReached: the business is past its hard spend limit of the
            day (no check wired: tests and autotests never stop).
    """

    if check is None:
        return

    verdict: SpendVerdict = check.run(
        SpendCheckRequest(
            business=turn.business,
            now=turn.received_at,
            model_id=turn.version.model_id,
        )
    )
    if verdict.level is SpendLevel.HARD_LIMIT:
        raise SpendLimitReached()
