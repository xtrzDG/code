import json

import pytest
from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.llm.tracing_llm_adapter import TracingLlmAdapter, extract_user_text
from app.facilitators.observability.sentry_error_reporting_facilitator import (
    scrub_event,
)
from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.conversations import LlmRequest, LlmToolDefinition
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
    SystemPromptText,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolInputJson,
    MessageText,
)
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.schemas.typings.platform.strings import (
    CorrelationId,
)

STARTED_AT_NANOSECONDS: int = 1_790_000_000_000_000_000


class RecordingTraceFacilitator:
    def __init__(self) -> None:
        self.traces: list[LlmGenerationTrace] = []

    def record_generation(self, trace: LlmGenerationTrace) -> None:
        self.traces.append(trace)

    def flush(self) -> None:
        return None


def build_request(adapter: ScriptedLlmAdapter) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId("gpt-5-mini"),
        system_prompt=SystemPromptText("You are the AI assistant."),
        tools=[
            LlmToolDefinition(
                name=AssistantToolName.GET_PRICE,
                description=LlmToolDescription("Price lookup."),
                input_schema_json=LlmToolInputSchemaJson('{"type": "object"}'),
            )
        ],
        transcript=[
            adapter.build_user_text_turn(MessageText("Сколько стоит хачапури?"))
        ],
        max_output_tokens=LlmMaxOutputTokens(1024),
        effort=LlmEffort.LOW,
    )


def build_tracing_adapter(
    inner: ScriptedLlmAdapter,
    facilitator: RecordingTraceFacilitator,
    is_content_traced: bool,
) -> TracingLlmAdapter:
    ticks: list[int] = [0, 1_500_000]
    return TracingLlmAdapter(
        inner_adapter=inner,
        trace_facilitator=facilitator,
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: STARTED_AT_NANOSECONDS,
        ),
        monotonic_clock=MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: ticks.pop(0) if ticks else 1_500_000,
        ),
        is_content_traced=is_content_traced,
    )


def test_tracing_adapter_records_metadata_without_content_by_default() -> None:
    inner = ScriptedLlmAdapter.from_turns(
        [
            ScriptedLlmTurn(
                tool_calls=[
                    ScriptedToolCall(
                        tool_name=AssistantToolName.GET_PRICE,
                        input_json=LlmToolInputJson('{"item_name": "хачапури"}'),
                    )
                ]
            )
        ]
    )
    facilitator = RecordingTraceFacilitator()
    adapter = build_tracing_adapter(inner, facilitator, is_content_traced=False)

    response = adapter.complete(build_request(inner))

    assert response.stop_reason is LlmStopReason.TOOL_USE
    trace = facilitator.traces[0]
    assert trace.model_id == "gpt-5-mini"
    assert trace.offered_tools == [AssistantToolName.GET_PRICE]
    assert trace.called_tools == [AssistantToolName.GET_PRICE]
    assert trace.elapsed == 1
    assert trace.input_text is None and trace.output_text is None


def test_tracing_adapter_captures_content_when_enabled_and_errors() -> None:
    inner = ScriptedLlmAdapter.from_turns(
        [ScriptedLlmTurn(text=MessageText("Хачапури стоит 18 ₾."))]
    )
    facilitator = RecordingTraceFacilitator()
    adapter = build_tracing_adapter(inner, facilitator, is_content_traced=True)
    request = build_request(inner)

    adapter.complete(request)
    with pytest.raises(ExternalServiceError):
        adapter.complete(request)

    assert facilitator.traces[0].input_text == "Сколько стоит хачапури?"
    assert facilitator.traces[0].output_text == "Хачапури стоит 18 ₾."
    assert facilitator.traces[1].error == "ExternalServiceError"


def test_extract_user_text_ignores_non_text_turns() -> None:
    assert extract_user_text(LlmProviderPayload("not json")) is None
    assert extract_user_text(LlmProviderPayload('{"role": "assistant"}')) is None
    assert (
        extract_user_text(
            LlmProviderPayload(
                json.dumps({"role": "user", "content": [{"type": "tool_result"}]})
            )
        )
        is None
    )


def build_trace() -> LlmGenerationTrace:
    return LlmGenerationTrace(
        trace_id=CorrelationId("trace-1"),
        model_id=LlmModelId("gpt-5-mini"),
        effort=LlmEffort.LOW,
        stop_reason=LlmStopReason.END_TURN,
        input_tokens=LlmTokenCount(120),
        output_tokens=LlmTokenCount(30),
        started_at=Microseconds(1_790_000_000_000_000),
        elapsed=ElapsedMilliseconds(250),
    )


def test_sentry_scrubber_removes_personal_data() -> None:
    event = scrub_event(
        {
            "message": "boom",
            "request": {"data": "+995555123456"},
            "user": {"id": "user_1"},
            "breadcrumbs": {"values": []},
        },
        {},
    )

    assert event is not None
    assert "request" not in event and "user" not in event
    assert event.get("message") == "boom"
