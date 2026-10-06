"""
The Anthropic Messages API through the real SDK client and adapter: the
documented answers (a tool_use turn, then text) match the SDK's types and
are read as a tool call and a reply; every request the adapter sends, a
photo included, matches the request type with every object closed;
documented errors become the platform's error.
"""

import json
from typing import Any

import httpx2
import pytest

from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmToolResult
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
)
from tests.brain.anthropic_adapter_helpers import build_request
from tests.brain.provider_http_fakes import ScriptedHttp, build_anthropic_client
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "anthropic_messages_api.json"
# A user turn with a photo, as the media resolver hands it to the adapter.
PHOTO_TURN = LlmProviderPayload(
    json.dumps(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "יש שולחן מחר בערב?"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwME",
                    },
                },
            ],
        },
        ensure_ascii=False,
    )
)


def answer(name: str) -> httpx2.Response:
    return httpx2.Response(200, json=load_json_fixture("anthropic", name))


@pytest.mark.parametrize("name", ["message_tool_use.json", "message_text.json"])
def test_documented_answers_match_the_sdk_types(name: str) -> None:
    assert_inbound(
        load_json_fixture("anthropic", name), SPEC, "response:messages.create"
    )


def test_photo_turn_tool_use_and_reply_round_trip() -> None:
    http = ScriptedHttp([answer("message_tool_use.json"), answer("message_text.json")])
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    first = adapter.complete(build_request([PHOTO_TURN]))
    tool_turn = adapter.build_tool_results_turn(
        [
            LlmToolResult(
                call_id=LlmToolCallId("toolu_01contract0001"),
                result_json=LlmToolResultJson('{"free": ["19:30"]}'),
            )
        ]
    )
    second = adapter.complete(
        build_request([PHOTO_TURN, first.assistant_turn_payload, tool_turn])
    )

    assert first.stop_reason is LlmStopReason.TOOL_USE
    [call] = first.tool_calls
    assert call.tool_name is AssistantToolName.CHECK_AVAILABILITY
    assert call.call_id == "toolu_01contract0001"
    assert json.loads(call.input_json) == {"date": "2026-10-05"}
    # Cache reads count as input.
    assert (first.input_tokens, first.output_tokens) == (1000, 35)
    assert second.stop_reason is LlmStopReason.END_TURN
    assert second.text == "יש שולחן פנוי ב-19:30."
    for index in range(2):
        assert_outbound(http.body(index), SPEC, "request:messages.create")
    photo_blocks: list[dict[str, Any]] = http.body(0)["messages"][0]["content"]
    assert [block["type"] for block in photo_blocks] == ["text", "image"]


@pytest.mark.parametrize(
    "case",
    load_json_fixture("anthropic", "anthropic_errors.json")["cases"],
    ids=lambda case: str(case["status"]),
)
def test_documented_errors_become_service_errors(case: dict[str, Any]) -> None:
    http = ScriptedHttp([httpx2.Response(case["status"], json=case["body"])])
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))

    with pytest.raises(ExternalServiceError) as raised:
        adapter.complete(build_request([PHOTO_TURN]))

    assert case["expected"] in str(raised.value)
