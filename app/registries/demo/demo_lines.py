"""
Short builders for the lines of demo conversations.

    customer("Do you have a table for four tonight?"),
    assistant("Yes, at 20:00 ...", tool(CHECK_AVAILABILITY, {...}, {...})),

Pauses are seconds after the previous line: customers take a while to
type, the assistant answers within seconds.
"""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.dto.demo_data import DemoMessageLine
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.schemas.typings.demo.constrained_integers import DemoReplyPauseSeconds
from app.utilities.conversations.llm_transcript import encode_json

CUSTOMER_PAUSE_SECONDS: int = 75
ASSISTANT_PAUSE_SECONDS: int = 6
STAFF_PAUSE_SECONDS: int = 300


def customer(text: str, pause: int = CUSTOMER_PAUSE_SECONDS) -> DemoMessageLine:
    return DemoMessageLine(
        author=MessageAuthor.CUSTOMER,
        text=MessageText(text),
        pause_seconds=DemoReplyPauseSeconds(pause),
    )


def assistant(
    text: str,
    *tool_calls: ToolCallRecord,
    pause: int = ASSISTANT_PAUSE_SECONDS,
) -> DemoMessageLine:
    return DemoMessageLine(
        author=MessageAuthor.ASSISTANT,
        text=MessageText(text),
        tool_calls=list(tool_calls),
        pause_seconds=DemoReplyPauseSeconds(pause),
    )


def staff(text: str, pause: int = STAFF_PAUSE_SECONDS) -> DemoMessageLine:
    return DemoMessageLine(
        author=MessageAuthor.STAFF,
        text=MessageText(text),
        pause_seconds=DemoReplyPauseSeconds(pause),
    )


def voice_tool(
    tool_call: ToolCallRecord,
    pause: int = ASSISTANT_PAUSE_SECONDS,
) -> DemoMessageLine:
    """A tool the voice agent called during a phone call (stored as SYSTEM)."""

    return DemoMessageLine(
        author=MessageAuthor.SYSTEM,
        text=MessageText(f"Voice agent called {tool_call.tool_name.value}."),
        tool_calls=[tool_call],
        pause_seconds=DemoReplyPauseSeconds(pause),
    )


def tool(
    name: AssistantToolName,
    arguments: dict[str, object],
    result: dict[str, object],
    is_error: bool = False,
) -> ToolCallRecord:
    """A tool call with its arguments and result as the model saw them."""

    return ToolCallRecord(
        tool_name=name,
        input_json=LlmToolInputJson(encode_json(arguments)),
        result_json=LlmToolResultJson(encode_json(result)),
        is_error=is_error,
    )
