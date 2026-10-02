"""A customer chat bounds every model call: its timeout and one retry."""

import httpx2
import pytest

from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.adapters.llm.call_limited_llm_adapter import (
    CHAT_CALL_RETRY_LIMIT,
    CallLimitedLlmAdapter,
)
from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.dto.conversations import LlmCallLimits, LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallRetryLimit,
    LlmCallTimeoutSeconds,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.brain.openai_adapter_helpers import build_request
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    anthropic_message,
    build_anthropic_client,
    build_openai_client,
    openai_message_item,
    openai_response,
)

CHAT_LIMITS: LlmCallLimits = LlmCallLimits(
    timeout_seconds=LlmCallTimeoutSeconds(25), retry_limit=CHAT_CALL_RETRY_LIMIT
)


def failing_once() -> httpx2.Response:
    # A tiny Retry-After keeps the SDK's backoff short in the test.
    return httpx2.Response(
        500,
        json={"error": {"type": "error", "message": "scripted failure"}},
        headers={"retry-after-ms": "10"},
    )


def limited(request: LlmRequest) -> LlmRequest:
    return request.model_copy(update={"call_limits": CHAT_LIMITS})


def test_a_chat_call_has_its_timeout_and_is_retried_once() -> None:
    http = ScriptedHttp(
        [failing_once(), openai_response([openai_message_item("Hello!")])]
    )
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    response = adapter.complete(
        limited(build_request([adapter.build_user_text_turn(MessageText("Hi"))]))
    )

    assert response.text == "Hello!"
    assert [
        request.headers["x-stainless-read-timeout"] for request in http.requests
    ] == [
        "25.0",
        "25.0",
    ]
    assert [
        request.headers["x-stainless-retry-count"] for request in http.requests
    ] == [
        "0",
        "1",
    ]


def test_a_second_failure_is_not_waited_out() -> None:
    http = ScriptedHttp([failing_once(), failing_once(), failing_once()])
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    with pytest.raises(ExternalServiceError, match="unavailable"):
        adapter.complete(
            limited(build_request([adapter.build_user_text_turn(MessageText("Hi"))]))
        )

    assert len(http.requests) == 2


def test_background_calls_keep_the_client_defaults() -> None:
    http = ScriptedHttp([failing_once()])
    adapter = OpenAiLlmAdapter(build_openai_client(http))

    with pytest.raises(ExternalServiceError):
        adapter.complete(
            build_request([adapter.build_user_text_turn(MessageText("Hi"))])
        )

    # The test SDK is built without retries; no limits leave that as it is.
    assert len(http.requests) == 1


def test_anthropic_calls_are_bounded_the_same_way() -> None:
    http = ScriptedHttp(
        [failing_once(), anthropic_message([{"type": "text", "text": "Hello!"}])]
    )
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))
    request = build_request([adapter.build_user_text_turn(MessageText("Hi"))])

    response = adapter.complete(
        limited(request.model_copy(update={"model_id": LlmModelId("claude-opus-5-5")}))
    )

    assert response.text == "Hello!"
    assert http.requests[0].headers["x-stainless-read-timeout"] == "25.0"
    assert http.requests[1].headers["x-stainless-retry-count"] == "1"


def test_the_chat_adapter_sets_the_limits_on_every_request() -> None:
    inner = ScriptedLlmAdapter.from_turns([ScriptedLlmTurn(text=MessageText("Hello!"))])
    adapter = CallLimitedLlmAdapter(inner, CHAT_LIMITS)
    turn = adapter.build_user_text_turn(MessageText("Hi"))

    adapter.complete(build_request([turn, adapter.build_tool_results_turn([])]))

    [request] = inner.requests
    assert request.call_limits == CHAT_LIMITS


def test_the_timeout_comes_from_the_settings() -> None:
    default = assemble_app_settings({})
    custom = assemble_app_settings({"LLM_CALL_TIMEOUT_SECONDS": "40"})

    assert default.llm_call_timeout_seconds == LlmCallTimeoutSeconds(25)
    assert custom.llm_call_timeout_seconds == LlmCallTimeoutSeconds(40)
    assert CHAT_CALL_RETRY_LIMIT == LlmCallRetryLimit(1)
