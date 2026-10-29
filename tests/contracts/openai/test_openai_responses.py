"""
The OpenAI Responses API through the real SDK client and adapter: the
documented answers (a function call, then a message) match OpenAI's
specification and are read as a tool call and a reply; every request the
adapter sends, a photo as `input_image` included, matches the
specification with every object closed; documented errors become the
platform's error.
"""

import json
from typing import Any

import httpx2
import pytest

from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmToolResult
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
)
from tests.brain.openai_adapter_helpers import build_request
from tests.brain.provider_http_fakes import ScriptedHttp, build_openai_client
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "openai_responses_api.json"
# A user turn with a photo, as the media resolver hands it to the adapter.
PHOTO_TURN = LlmProviderPayload(
    json.dumps(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "რა ღირს ეს?"},
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
    return httpx2.Response(200, json=load_json_fixture("openai", name))


@pytest.mark.parametrize(
    "name", ["response_function_call.json", "response_message.json"]
)
def test_documented_answers_match_the_specification(name: str) -> None:
    assert_inbound(load_json_fixture("openai", name), SPEC, "Response")


def test_photo_turn_tool_call_and_reply_round_trip() -> None:
    http = ScriptedHttp(
        [answer("response_function_call.json"), answer("response_message.json")]
    )
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    first = adapter.complete(build_request([PHOTO_TURN]))
    tool_turn = adapter.build_tool_results_turn(
        [
            LlmToolResult(
                call_id=LlmToolCallId("call_0contract0001"),
                result_json=LlmToolResultJson('{"price":"18.00","currency":"GEL"}'),
            )
        ]
    )
    second = adapter.complete(
        build_request([PHOTO_TURN, first.assistant_turn_payload, tool_turn])
    )

    assert first.stop_reason is LlmStopReason.TOOL_USE
    [call] = first.tool_calls
    assert call.tool_name is AssistantToolName.GET_PRICE
    assert json.loads(call.input_json) == {"item_name": "ხაჭაპური"}
    assert (first.input_tokens, first.output_tokens) == (1500, 60)
    assert second.stop_reason is LlmStopReason.END_TURN
    assert second.text == "აჭარული ხაჭაპური ღირს 18 ₾."
    for index in range(2):
        assert_outbound(http.body(index), SPEC, "request:responses.create")
    photo_parts: list[dict[str, Any]] = http.body(0)["input"][0]["content"]
    assert [part["type"] for part in photo_parts] == ["input_text", "input_image"]


@pytest.mark.parametrize(
    "case",
    load_json_fixture("openai", "openai_errors.json")["cases"],
    ids=lambda case: str(case["status"]),
)
def test_documented_errors_become_service_errors(case: dict[str, Any]) -> None:
    http = ScriptedHttp([httpx2.Response(case["status"], json=case["body"])])
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    with pytest.raises(ExternalServiceError) as raised:
        adapter.complete(build_request([PHOTO_TURN]))

    assert case["expected"] in str(raised.value)
