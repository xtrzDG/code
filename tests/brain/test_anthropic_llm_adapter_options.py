"""Anthropic adapter options, stop reasons, refusals and errors."""

import anthropic
import pytest

from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.strings import MessageText
from tests.brain.anthropic_adapter_helpers import build_request
from tests.brain.provider_http_fakes import (
    ScriptedHttp,
    anthropic_message,
    build_anthropic_client,
    error_response,
)


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


@pytest.mark.parametrize(
    ("model_id", "has_effort", "has_fallbacks"),
    [
        ("claude-opus-5-5", True, True),
        ("claude-sonnet-5-5", True, True),
        ("claude-sonnet-4-6", True, False),
        ("claude-haiku-4-5", False, False),
        ("claude-haiku-4-5-20251001", False, False),
    ],
)
def test_only_options_the_model_accepts_are_sent(
    model_id: str,
    has_effort: bool,
    has_fallbacks: bool,
) -> None:
    http = ScriptedHttp([anthropic_message([{"type": "text", "text": "Hi"}])])
    adapter = AnthropicLlmAdapter(build_anthropic_client(http))
    request = build_request([adapter.build_user_text_turn(MessageText("Hi"))])

    adapter.complete(request.model_copy(update={"model_id": LlmModelId(model_id)}))

    body = http.body(0)
    assert ("output_config" in body) is has_effort
    assert ("fallbacks" in body) is has_fallbacks
    assert ("anthropic-beta" in http.requests[0].headers) is has_fallbacks
