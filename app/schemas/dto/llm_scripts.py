from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText


class ScriptedToolCall(ImmutableDTO):
    """Tool call the scripted language model will request."""

    tool_name: AssistantToolName
    input_json: LlmToolInputJson


class ScriptedLlmTurn(ImmutableDTO):
    """One scripted model answer: text, tool calls, or both."""

    text: MessageText | None = None
    tool_calls: list[ScriptedToolCall] = Field(default_factory=list[ScriptedToolCall])
