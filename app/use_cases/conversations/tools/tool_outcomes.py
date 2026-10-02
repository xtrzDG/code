"""The result of a tool call as the model receives it."""

from app.schemas.dto.assistant_tools import AssistantToolOutcome
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.utilities.conversations.tool_payloads import render_tool_error


def success_outcome(
    call: LlmToolCall,
    result_json: LlmToolResultJson,
) -> AssistantToolOutcome:
    return AssistantToolOutcome(
        tool_name=call.tool_name,
        result=LlmToolResult(call_id=call.call_id, result_json=result_json),
    )


def error_outcome(call: LlmToolCall, message: str) -> AssistantToolOutcome:
    return AssistantToolOutcome(
        tool_name=call.tool_name,
        result=LlmToolResult(
            call_id=call.call_id,
            result_json=render_tool_error(message),
            is_error=True,
        ),
    )
