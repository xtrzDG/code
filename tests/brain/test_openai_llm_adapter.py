import json
from typing import Any

import openai
import pytest

from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
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
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolCallId,
    LlmToolResultJson,
    MessageText,
)
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    build_openai_client,
    error_response,
    openai_function_call_item,
    openai_message_item,
    openai_reasoning_item,
    openai_response,
)

PRICE_TOOL = LlmToolDefinition(
    name=AssistantToolName.GET_PRICE,
    description=LlmToolDescription("Look up a price."),
    input_schema_json=LlmToolInputSchemaJson(
        json.dumps(
            {
                "type": "object",
                "properties": {"item_name": {"type": "string"}},
                "required": ["item_name"],
                "additionalProperties": False,
            }
        )
    ),
)


def build_request(
    transcript: list[LlmProviderPayload],
    effort: LlmEffort = LlmEffort.LOW,
) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId("gpt-5-mini"),
        system_prompt=SystemPromptText("You are the AI assistant of Sakhli."),
        tools=[PRICE_TOOL],
        transcript=transcript,
        max_output_tokens=LlmMaxOutputTokens(4000),
        effort=effort,
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


@pytest.mark.parametrize(
    ("effort", "wire_effort"),
    [
        (LlmEffort.MINIMAL, "minimal"),
        (LlmEffort.LOW, "low"),
        (LlmEffort.MEDIUM, "medium"),
        (LlmEffort.HIGH, "high"),
    ],
)
def test_effort_maps_to_reasoning_effort(effort: LlmEffort, wire_effort: str) -> None:
    http = ScriptedHttp([openai_response([openai_message_item("Hello!")])])
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    adapter.complete(
        build_request([adapter.build_user_text_turn(MessageText("Hi"))], effort)
    )

    assert http.body(0)["reasoning"] == {"effort": wire_effort}


def test_incomplete_response_maps_to_max_tokens() -> None:
    http = ScriptedHttp(
        [
            openai_response(
                [openai_message_item("Our menu has many dishes, for exam")],
                status="incomplete",
                incomplete_reason="max_output_tokens",
            )
        ]
    )
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    response = adapter.complete(
        build_request([adapter.build_user_text_turn(MessageText("Menu?"))])
    )

    assert response.stop_reason is LlmStopReason.MAX_TOKENS
    assert response.text == "Our menu has many dishes, for exam"


def test_refusal_and_content_filter_raise_llm_refused() -> None:
    refusal_item = {
        "type": "message",
        "id": "msg_refusal",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "refusal", "refusal": "I can't help with that."}],
    }
    http = ScriptedHttp(
        [
            openai_response([refusal_item]),
            openai_response(
                [], status="incomplete", incomplete_reason="content_filter"
            ),
        ]
    )
    adapter = OpenAiLlmAdapter(build_openai_client(http))
    request = build_request([adapter.build_user_text_turn(MessageText("..."))])

    with pytest.raises(LlmRefusedError):
        adapter.complete(request)

    with pytest.raises(LlmRefusedError):
        adapter.complete(request)


def test_unknown_tool_and_failed_response_are_provider_errors() -> None:
    failed = openai_response([], status="failed")
    failed_body = json.loads(failed.content)
    failed_body["error"] = {"code": "server_error", "message": "boom"}
    http = ScriptedHttp(
        [
            openai_response([openai_function_call_item("delete_database", {})]),
            type(failed)(200, json=failed_body),
        ]
    )
    adapter = OpenAiLlmAdapter(build_openai_client(http))
    request = build_request([adapter.build_user_text_turn(MessageText("hi"))])

    with pytest.raises(ExternalServiceError, match="unknown tool"):
        adapter.complete(request)

    with pytest.raises(ExternalServiceError, match="server_error"):
        adapter.complete(request)


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (400, "rejected the request"),
        (401, "API key"),
        (403, "denied access"),
        (404, "does not serve model"),
        (422, "rejected the request"),
        (429, "rate limit"),
        (500, "unavailable"),
        (503, "unavailable"),
        (418, "HTTP 418"),
    ],
)
def test_http_errors_become_external_service_errors(
    status_code: int,
    message: str,
) -> None:
    http = ScriptedHttp([error_response(status_code)])
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    with pytest.raises(ExternalServiceError, match=message):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("hi"))])
        )


def test_missing_api_key_is_reported_on_first_use_not_at_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAiResponsesClient(
        base_url=PublicBaseUrl("https://eu.api.openai.com/v1"),
        project_id=None,
    )
    adapter = OpenAiLlmAdapter(client)

    with pytest.raises(ExternalServiceError, match="OPENAI_API_KEY"):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("hi"))])
        )


def test_connection_failures_become_external_service_errors() -> None:
    def failing_sdk() -> openai.OpenAI:
        import httpx2

        def refuse(request: httpx2.Request) -> httpx2.Response:
            raise httpx2.ConnectError("refused", request=request)

        return openai.OpenAI(
            api_key="sk-test",
            base_url="https://eu.api.openai.com/v1",
            http_client=httpx2.Client(transport=httpx2.MockTransport(refuse)),
            max_retries=0,
        )

    client = OpenAiResponsesClient(
        base_url=PublicBaseUrl("https://eu.api.openai.com/v1"),
        project_id=None,
        sdk_factory=failing_sdk,
    )
    adapter = OpenAiLlmAdapter(client)

    with pytest.raises(ExternalServiceError, match="cannot be reached"):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("hi"))])
        )


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
