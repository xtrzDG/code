"""
The limits of one reply turn beyond its rounds and the business's spend
(AI-09, OWASP LLM10 Unbounded Consumption):

- a conversation answers on at most `CONVERSATION_TOKEN_BUDGET` model
  tokens, input and output of every reply so far and of this turn; past
  them no further model call is made;
- one turn runs at most `TURN_WALL_CLOCK_LIMIT`: no round starts after it
  (one slow model call still ends at its own timeout);
- a tool called with the same input more than `MAX_IDENTICAL_TOOL_CALLS`
  times in one turn does not run again (the model gets an error result,
  as every call needs one); a model that repeats it in a later round
  anyway is in a loop, and no further round starts.

Each of them ends the turn as unanswered: the conversation goes to a
colleague, who sees why (ANSWER_UNFINISHED), and the customer hears so.
"""

import json
from dataclasses import dataclass
from datetime import timedelta

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.dto.assistant_tools import AssistantToolOutcome
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.conversations import LlmToolCall
from app.use_cases.conversations.replies.turn_progress import TurnProgress
from app.use_cases.conversations.tools.tool_outcomes import error_outcome
from app.use_cases.shared.turn_time import to_microseconds

CONVERSATION_TOKEN_BUDGET: int = 2_000_000
TURN_WALL_CLOCK_LIMIT: timedelta = timedelta(seconds=120)
MAX_IDENTICAL_TOOL_CALLS: int = 2
REPEATED_CALL: str = (
    "Not run: {tool} was already called {count} times with this same input in "
    "this turn. Use its earlier result, or offer to pass the question to a "
    "colleague."
)


class TurnBudgetSpent(Exception):
    """A limit of the turn was reached: no further round (technical)."""


@dataclass(frozen=True)
class TurnBudget:
    """Where the turn started: the conversation's tokens and the time."""

    tokens_before: int
    started_at: Microseconds


def start_budget(
    message_repo: MessageRepoContract, turn: PreparedTurn, now: Microseconds
) -> TurnBudget:
    """The budget of a turn starting now, after the conversation's replies."""

    messages = message_repo.list_by_conversation(turn.business.id, turn.conversation.id)
    return TurnBudget(
        tokens_before=sum(
            int(message.input_tokens) + int(message.output_tokens)
            for message in messages
            if message.author is MessageAuthor.ASSISTANT
        ),
        started_at=now,
    )


def check_turn_budget(
    budget: TurnBudget, progress: TurnProgress, now: Microseconds
) -> None:
    """
    Raises:
        TurnBudgetSpent: the conversation's tokens, the turn's time or a
            tool loop leave no room for another round.
    """

    tokens: int = budget.tokens_before + progress.input_tokens + progress.output_tokens
    if tokens >= CONVERSATION_TOKEN_BUDGET:
        raise TurnBudgetSpent("The conversation's token budget is spent.")

    elapsed: int = int(now) - int(budget.started_at)
    if elapsed >= to_microseconds(TURN_WALL_CLOCK_LIMIT):
        raise TurnBudgetSpent("The turn ran out of time.")

    if progress.repeat_rounds > 1:
        raise TurnBudgetSpent("The model repeats the same tool call.")


def repeated_call_outcome(
    progress: TurnProgress, call: LlmToolCall
) -> AssistantToolOutcome | None:
    """The error result of a call made too often already; None to run it."""

    key: tuple[str, str] = (str(call.tool_name), canonical_input(str(call.input_json)))
    count: int = sum(1 for made in progress.tool_calls if call_key(made) == key)
    if count < MAX_IDENTICAL_TOOL_CALLS:
        return None

    return error_outcome(
        call, REPEATED_CALL.format(tool=str(call.tool_name), count=count)
    )


def call_key(call: ToolCallRecord) -> tuple[str, str]:
    """A tool call's name and its input in one canonical spelling."""

    return (str(call.tool_name), canonical_input(str(call.input_json)))


def canonical_input(input_json: str) -> str:
    """The input with sorted keys, so key order does not hide a repeat."""

    try:
        return json.dumps(json.loads(input_json), sort_keys=True, ensure_ascii=False)
    except ValueError:
        return input_json.strip()
