import json
from typing import Any

import anthropic
import pytest

from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmToolDefinition,
    LlmToolResult,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    anthropic_message,
    build_anthropic_client,
    error_response,
)

AVAILABILITY_TOOL = LlmToolDefinition(
    name=AssistantToolName.CHECK_AVAILABILITY,
    description=LlmToolDescription("Check free slots."),
    input_schema_json=LlmToolInputSchemaJson(
        json.dumps(
            {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
                "additionalProperties": False,
            }
        )
    ),
)


def build_request(
    transcript: list[LlmProviderPayload],
    effort: LlmEffort = LlmEffort.MEDIUM,
) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId("claude-opus-5-5"),
        system_prompt=SystemPromptText("You are the AI assistant of Beit Kafe."),
        tools=[AVAILABILITY_TOOL],
        transcript=transcript,
        max_output_tokens=LlmMaxOutputTokens(16000),
        effort=effort,
    )


def test_tool_use_turn_is_stored_verbatim_and_replayed_unchanged() -> None:
    thinking_block = {"type": "thinking", "thinking": "", "signature": "sig-1"}
    tool_use_block = {
        "type": "tool_use",
        "id": "toolu_01",
        "name": "check_availability",
        "input": {"date": "2026-10-05"},
    }
    http = ScriptedHttp(
        [
            anthropic_message(
                [thinking_block, {"type": "text", "text": "בודק..."}, tool_use_block],
                "tool_use",
                input_tokens=120,
                cache_read_tokens=880,
                output_tokens=35,
            ),
            anthropic_message(
                [{"type": "text", "text": "יש שולחן פנוי ב-19:30."}], "end_turn"
            ),
        ]
    )
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))
    user_turn = adapter.build_user_text_turn(MessageText("יש שולחן מחר בערב?"))

    first = adapter.complete(build_request([user_turn]))

    assert first.stop_reason is LlmStopReason.TOOL_USE
    assert first.text == "בודק..."
    assert first.tool_calls[0].tool_name is AssistantToolName.CHECK_AVAILABILITY
    assert first.tool_calls[0].call_id == "toolu_01"
    assert json.loads(first.tool_calls[0].input_json) == {"date": "2026-10-05"}
    assert (first.input_tokens, first.output_tokens) == (1000, 35)
    stored_turn = json.loads(first.assistant_turn_payload)
    assert stored_turn == {
        "role": "assistant",
        "content": [
            thinking_block,
            {"type": "text", "text": "בודק..."},
            tool_use_block,
        ],
    }

    tool_turn = adapter.build_tool_results_turn(
        [
            LlmToolResult(
                call_id=LlmToolCallId("toolu_01"),
                result_json=LlmToolResultJson('{"slots":[{"time":"19:30"}]}'),
            )
        ]
    )
    second = adapter.complete(
        build_request([user_turn, first.assistant_turn_payload, tool_turn])
    )

    assert second.stop_reason is LlmStopReason.END_TURN
    assert second.text == "יש שולחן פנוי ב-19:30."
    first_body: dict[str, Any] = http.body(0)
    assert first_body["model"] == "claude-opus-5-5"
    assert first_body["max_tokens"] == 16000
    assert first_body["system"] == [
        {
            "type": "text",
            "text": "You are the AI assistant of Beit Kafe.",
            "cache_control": {"type": "ephemeral"},
        }
    ]
    assert first_body["tools"] == [
        {
            "name": "check_availability",
            "description": "Check free slots.",
            "input_schema": json.loads(AVAILABILITY_TOOL.input_schema_json),
            "strict": True,
        }
    ]
    assert first_body["output_config"] == {"effort": "medium"}
    assert first_body["fallbacks"] == "default"
    assert first_body["cache_control"] == {"type": "ephemeral"}
    assert "thinking" not in first_body
    assert "tool_choice" not in first_body
    assert (
        http.requests[0].headers["anthropic-beta"] == "server-side-fallback-2026-07-01"
    )
    assert http.body(1)["messages"] == [
        json.loads(user_turn),
        stored_turn,
        json.loads(tool_turn),
    ]


@pytest.mark.parametrize(
    ("effort", "wire_effort"),
    [
        (LlmEffort.MINIMAL, "low"),
        (LlmEffort.LOW, "low"),
        (LlmEffort.MEDIUM, "medium"),
        (LlmEffort.HIGH, "high"),
    ],
)
def test_effort_maps_to_output_config(effort: LlmEffort, wire_effort: str) -> None:
    http = ScriptedHttp([anthropic_message([{"type": "text", "text": "Hi"}])])
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    adapter.complete(
        build_request([adapter.build_user_text_turn(MessageText("Hi"))], effort)
    )

    assert http.body(0)["output_config"] == {"effort": wire_effort}


@pytest.mark.parametrize(
    ("stop_reason", "expected"),
    [
        ("end_turn", LlmStopReason.END_TURN),
        ("stop_sequence", LlmStopReason.END_TURN),
        ("max_tokens", LlmStopReason.MAX_TOKENS),
        ("model_context_window_exceeded", LlmStopReason.MAX_TOKENS),
        ("pause_turn", LlmStopReason.PAUSE_TURN),
        ("compaction", LlmStopReason.OTHER),
    ],
)
def test_stop_reasons_are_normalized(
    stop_reason: str,
    expected: LlmStopReason,
) -> None:
    http = ScriptedHttp(
        [anthropic_message([{"type": "text", "text": "..."}], stop_reason)]
    )
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    response = adapter.complete(
        build_request([adapter.build_user_text_turn(MessageText("Hi"))])
    )

    assert response.stop_reason is expected


def test_refusal_is_checked_before_content() -> None:
    http = ScriptedHttp(
        [
            anthropic_message(
                [{"type": "text", "text": "partial answer"}],
                "refusal",
            )
        ]
    )
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    with pytest.raises(LlmRefusedError):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("..."))])
        )


def test_fallback_blocks_are_kept_for_replay() -> None:
    fallback_block = {
        "type": "fallback",
        "from": {"model": "claude-opus-5-5"},
        "to": {"model": "claude-opus-5"},
    }
    http = ScriptedHttp(
        [
            anthropic_message(
                [fallback_block, {"type": "text", "text": "Здравствуйте!"}],
                "end_turn",
            )
        ]
    )
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    response = adapter.complete(
        build_request([adapter.build_user_text_turn(MessageText("Привет"))])
    )

    stored_content = json.loads(response.assistant_turn_payload)["content"]
    assert stored_content[0]["type"] == "fallback"
    assert stored_content[0]["from"] == {"model": "claude-opus-5-5"}
    assert response.text == "Здравствуйте!"


def test_openai_turns_are_converted_for_replay() -> None:
    http = ScriptedHttp([anthropic_message([{"type": "text", "text": "OK"}])])
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))
    openai_turn = LlmProviderPayload(
        json.dumps(
            {
                "role": "assistant",
                "provider": "openai",
                "items": [
                    {"type": "reasoning", "id": "rs_1", "summary": []},
                    {
                        "type": "message",
                        "id": "msg_1",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": "Checking."}],
                    },
                    {
                        "type": "function_call",
                        "call_id": "call_9",
                        "name": "check_availability",
                        "arguments": '{"date": "2026-10-05"}',
                    },
                ],
            }
        )
    )
    reasoning_only_turn = LlmProviderPayload(
        json.dumps(
            {
                "role": "assistant",
                "provider": "openai",
                "items": [{"type": "reasoning", "id": "rs_2", "summary": []}],
            }
        )
    )

    adapter.complete(
        build_request(
            [
                adapter.build_user_text_turn(MessageText("Table tomorrow?")),
                openai_turn,
                reasoning_only_turn,
            ]
        )
    )

    assert http.body(0)["messages"][1:] == [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Checking."},
                {
                    "type": "tool_use",
                    "id": "call_9",
                    "name": "check_availability",
                    "input": {"date": "2026-10-05"},
                },
            ],
        }
    ]


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (400, "rejected the request"),
        (401, "API key"),
        (403, "denied access"),
        (404, "does not serve model"),
        (413, "rejected the request"),
        (429, "rate limit"),
        (500, "unavailable"),
        (529, "unavailable"),
        (418, "HTTP 418"),
    ],
)
def test_http_errors_become_external_service_errors(
    status_code: int,
    message: str,
) -> None:
    http = ScriptedHttp([error_response(status_code)])
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    with pytest.raises(ExternalServiceError, match=message):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("hi"))])
        )


def test_unknown_tool_is_a_provider_error() -> None:
    http = ScriptedHttp(
        [
            anthropic_message(
                [{"type": "tool_use", "id": "toolu_x", "name": "rm_rf", "input": {}}],
                "tool_use",
            )
        ]
    )
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    with pytest.raises(ExternalServiceError, match="unknown tool"):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("hi"))])
        )


def test_sdk_construction_failure_is_reported_as_configuration_error() -> None:
    def broken_sdk() -> anthropic.Anthropic:
        raise anthropic.AnthropicError("no credentials")

    adapter = AnthropicLlmAdapter(AnthropicMessagesClient(sdk_factory=broken_sdk))

    with pytest.raises(ExternalServiceError, match="ANTHROPIC_API_KEY"):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("hi"))])
        )
