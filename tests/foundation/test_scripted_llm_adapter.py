import json

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmRequest, LlmToolResult
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)


def test_scripted_adapter_returns_tool_calls_then_text() -> None:
    adapter = ScriptedLlmAdapter.from_turns(
        [
            ScriptedLlmTurn(
                tool_calls=[
                    ScriptedToolCall(
                        tool_name=AssistantToolName.CHECK_AVAILABILITY,
                        input_json=LlmToolInputJson('{"date": "2026-10-05"}'),
                    )
                ]
            ),
            ScriptedLlmTurn(text=MessageText("Есть столик на 19:30.")),
        ]
    )
    user_turn = adapter.build_user_text_turn(MessageText("Столик на завтра?"))
    request = LlmRequest(
        model_id=LlmModelId("claude-opus-5-5"),
        system_prompt=SystemPromptText("You are the AI assistant."),
        tools=[],
        transcript=[user_turn],
        max_output_tokens=LlmMaxOutputTokens(1024),
        effort=LlmEffort.LOW,
    )

    first = adapter.complete(request)
    assert first.stop_reason is LlmStopReason.TOOL_USE
    assert first.tool_calls[0].tool_name is AssistantToolName.CHECK_AVAILABILITY
    tool_turn = adapter.build_tool_results_turn(
        [
            LlmToolResult(
                call_id=first.tool_calls[0].call_id,
                result_json=LlmToolResultJson('{"slots": []}'),
            )
        ]
    )
    assert json.loads(tool_turn)["content"][0]["tool_use_id"] == str(
        first.tool_calls[0].call_id
    )

    second = adapter.complete(request)
    assert second.stop_reason is LlmStopReason.END_TURN
    assert second.text == "Есть столик на 19:30."
    assert json.loads(user_turn)["content"][0]["text"] == "Столик на завтра?"
    assert len(adapter.requests) == 2
