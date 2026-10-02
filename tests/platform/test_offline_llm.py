"""LLM_PROVIDER=scripted: the offline model a staging deployment answers with."""

import json

from app.adapters.llm.offline_llm_adapter import OFFLINE_REPLY, OfflineLlmAdapter
from app.containers.app import AppContainer
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmRequest, LlmToolResult
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import (
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider


def build_request(model_id: str) -> LlmRequest:
    adapter = OfflineLlmAdapter()
    return LlmRequest(
        model_id=LlmModelId(model_id),
        system_prompt=SystemPromptText("You are the assistant of a bakery."),
        tools=[],
        transcript=[adapter.build_user_text_turn(MessageText("Are you open?"))],
        max_output_tokens=LlmMaxOutputTokens(1000),
        effort=LlmEffort.LOW,
    )


def test_every_turn_gets_the_fixed_reply_without_tools() -> None:
    response = OfflineLlmAdapter().complete(build_request("scripted"))

    assert response.stop_reason is LlmStopReason.END_TURN
    assert response.text == OFFLINE_REPLY
    assert response.tool_calls == []
    assert json.loads(str(response.assistant_turn_payload)) == {
        "role": "assistant",
        "content": [{"type": "text", "text": str(OFFLINE_REPLY)}],
    }


def test_turn_payloads_are_the_canonical_ones() -> None:
    adapter = OfflineLlmAdapter()
    results = adapter.build_tool_results_turn(
        [
            LlmToolResult(
                call_id=LlmToolCallId("toolu_1"),
                result_json=LlmToolResultJson('{"ok": true}'),
            )
        ]
    )

    assert json.loads(str(results))["content"][0]["tool_use_id"] == "toolu_1"


def test_the_application_routes_the_scripted_model_to_it() -> None:
    container = AppContainer()
    replace_provider(
        container.config.app_settings,
        assemble_app_settings({"LLM_PROVIDER": "scripted"}),
    )

    response = container.adapters.routing_llm_adapter().complete(
        build_request(str(container.config.app_settings().llm_model_id))
    )

    assert response.text == OFFLINE_REPLY
