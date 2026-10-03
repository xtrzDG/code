"""
OpenAI adapter turns: stored verbatim, Anthropic turns replayed, corrupted ones refused.
"""

import json
from typing import Any

import pytest

from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import (
    LlmToolResult,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from tests.brain.openai_adapter_helpers import PRICE_TOOL, build_request
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    build_openai_client,
    openai_function_call_item,
    openai_message_item,
    openai_reasoning_item,
    openai_response,
)


def test_tool_call_turn_is_stored_verbatim_and_replayed_unchanged() -> None:
    http = ScriptedHttp(
        [
            openai_response(
                [
                    openai_reasoning_item("rs_1"),
                    openai_function_call_item(
                        "get_price", {"item_name": "ხაჭაპური"}, call_id="call_7"
                    ),
                ],
                input_tokens=1500,
                output_tokens=60,
            ),
            openai_response(
                [
                    openai_reasoning_item("rs_2"),
                    openai_message_item("აჭარული ხაჭაპური ღირს 18 ₾."),
                ]
            ),
        ]
    )
    adapter = OpenAiLlmAdapter(build_openai_client(http))
    user_turn = adapter.build_user_text_turn(MessageText("რა ღირს ხაჭაპური?"))

    first = adapter.complete(build_request([user_turn]))

    assert first.stop_reason is LlmStopReason.TOOL_USE
    assert first.text is None
    assert [call.tool_name for call in first.tool_calls] == [
        AssistantToolName.GET_PRICE
    ]
    assert first.tool_calls[0].call_id == "call_7"
    assert json.loads(first.tool_calls[0].input_json) == {"item_name": "ხაჭაპური"}
    assert (first.input_tokens, first.output_tokens) == (1500, 60)
    stored_turn = json.loads(first.assistant_turn_payload)
    assert stored_turn["role"] == "assistant"
    assert stored_turn["provider"] == "openai"
    assert stored_turn["items"][0]["encrypted_content"] == "gAAAA-encrypted-rs_1"

    tool_turn = adapter.build_tool_results_turn(
        [
            LlmToolResult(
                call_id=LlmToolCallId("call_7"),
                result_json=LlmToolResultJson('{"price":"18.00","currency":"GEL"}'),
            )
        ]
    )
    second = adapter.complete(
        build_request([user_turn, first.assistant_turn_payload, tool_turn])
    )

    assert second.stop_reason is LlmStopReason.END_TURN
    assert second.text == "აჭარული ხაჭაპური ღირს 18 ₾."
    first_body: dict[str, Any] = http.body(0)
    assert first_body["model"] == "gpt-5-mini"
    assert first_body["instructions"] == "You are the AI assistant of Sakhli."
    assert first_body["store"] is False
    assert first_body["include"] == ["reasoning.encrypted_content"]
    assert first_body["reasoning"] == {"effort": "low"}
    assert first_body["max_output_tokens"] == 4000
    assert first_body["tools"] == [
        {
            "type": "function",
            "name": "get_price",
            "description": "Look up a price.",
            "parameters": json.loads(PRICE_TOOL.input_schema_json),
            "strict": True,
        }
    ]
    assert first_body["input"] == [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "რა ღირს ხაჭაპური?"}],
        }
    ]
    second_input: list[dict[str, Any]] = http.body(1)["input"]
    assert second_input[0] == first_body["input"][0]
    assert second_input[1:3] == stored_turn["items"]
    assert second_input[3] == {
        "type": "function_call_output",
        "call_id": "call_7",
        "output": '{"price":"18.00","currency":"GEL"}',
    }
    assert http.requests[0].headers["openai-project"] == "proj_eu_restaurants"
    assert str(http.requests[0].url) == "https://eu.api.openai.com/v1/responses"


def test_anthropic_format_turns_are_converted_for_replay() -> None:
    http = ScriptedHttp([openai_response([openai_message_item("Готово!")])])
    adapter = OpenAiLlmAdapter(build_openai_client(http))
    scripted_assistant_turn = LlmProviderPayload(
        json.dumps(
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "", "signature": "x"},
                    {"type": "text", "text": "Проверяю."},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "get_price",
                        "input": {"item_name": "Борщ"},
                    },
                ],
            },
            ensure_ascii=False,
        )
    )
    mixed_user_turn = LlmProviderPayload(
        json.dumps(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": [{"type": "text", "text": '{"price":"9.00"}'}],
                    },
                    {"type": "text", "text": "А десерты?"},
                ],
            },
            ensure_ascii=False,
        )
    )

    adapter.complete(
        build_request(
            [
                adapter.build_user_text_turn(MessageText("Сколько стоит борщ?")),
                scripted_assistant_turn,
                mixed_user_turn,
            ]
        )
    )

    assert http.body(0)["input"][1:] == [
        {"role": "assistant", "content": "Проверяю."},
        {
            "type": "function_call",
            "call_id": "toolu_1",
            "name": "get_price",
            "arguments": '{"item_name":"Борщ"}',
        },
        {
            "type": "function_call_output",
            "call_id": "toolu_1",
            "output": '{"price":"9.00"}',
        },
        {"role": "user", "content": [{"type": "input_text", "text": "А десерты?"}]},
    ]


def test_corrupted_transcript_is_a_provider_error() -> None:
    adapter = OpenAiLlmAdapter(build_openai_client(ScriptedHttp([])))

    for broken_payload in ("not json", "[1, 2]", '{"role": "system"}'):
        with pytest.raises(ExternalServiceError):
            adapter.complete(build_request([LlmProviderPayload(broken_payload)]))
