"""
Anthropic adapter turns: stored verbatim, fallback blocks and OpenAI turns replayed.
"""

import json
from typing import Any

from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import (
    LlmToolResult,
)
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from tests.brain.anthropic_adapter_helpers import AVAILABILITY_TOOL, build_request
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    anthropic_message,
    build_anthropic_client,
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
