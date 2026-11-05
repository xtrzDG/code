"""OpenAI adapter options, incomplete responses, refusals and errors."""

import json

import openai
import pytest

from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import MessageText
from tests.brain.openai_adapter_helpers import build_request
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    build_openai_client,
    error_response,
    openai_function_call_item,
    openai_message_item,
    openai_response,
)


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
