"""
The quality journal over Langfuse's OpenTelemetry ingestion: a model call
becomes one OTLP/JSON span (a trace with one `generation` observation), the
client posts an `ExportTraceServiceRequest` with basic auth and the
ingestion-version header, and delivery failures never reach the caller.
"""

import base64
import json
from typing import Any, cast

import httpx
import pytest
from typed_time_provider import Microseconds

from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.facilitators.observability.langfuse_otel_spans import (
    build_generation_span,
    otel_trace_id,
)
from app.facilitators.observability.langfuse_trace_facilitator import (
    LangfuseTraceFacilitator,
)
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.observability.constrained_strings import TraceId
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.schemas.typings.platform.constrained_strings import RequestId
from app.schemas.typings.platform.strings import (
    CorrelationId,
    JobErrorText,
    PlatformIdentifier,
    PlatformSecret,
)
from tests.platform.test_observability import build_trace

UUID_TRACE_ID: str = "0f8fad5b-d9cb-469f-a165-70867728950e"


def attributes_of(span: dict[str, object]) -> dict[str, str]:
    """The span's attributes by key (all of them are string values)."""

    pairs = cast(list[dict[str, Any]], span["attributes"])
    return {pair["key"]: pair["value"]["stringValue"] for pair in pairs}


def langfuse_client(transport: httpx.BaseTransport) -> LangfuseIngestionClient:
    return LangfuseIngestionClient(
        host=PublicBaseUrl("https://cloud.langfuse.com/"),
        public_key=PlatformIdentifier("pk-lf-test-0000"),
        secret_key=PlatformSecret("sk-lf-test-0000"),
        transport=transport,
    )


def test_a_call_is_one_root_generation_span_of_its_own_trace() -> None:
    span = build_generation_span(build_trace())
    attributes = attributes_of(span)

    assert span["name"] == "assistant_reply"
    assert "parentSpanId" not in span  # the root: Langfuse makes it the trace
    assert "status" not in span
    assert attributes["langfuse.observation.type"] == "generation"
    assert attributes["langfuse.trace.name"] == "assistant_reply"
    assert attributes["langfuse.observation.model.name"] == "gpt-5-mini"
    assert attributes["langfuse.observation.level"] == "DEFAULT"
    assert json.loads(attributes["langfuse.observation.usage_details"]) == {
        "input": 120,
        "output": 30,
        "total": 150,
    }
    assert attributes["langfuse.trace.metadata.model"] == "gpt-5-mini"
    assert attributes["langfuse.observation.metadata.effort"] == "low"
    assert attributes["langfuse.observation.metadata.stop_reason"] == "end_turn"
    assert attributes["langfuse.observation.metadata.elapsed_ms"] == "250"
    assert attributes["langfuse.observation.metadata.offered_tools"] == "[]"


def test_ids_are_otel_hex_and_stable_and_times_are_unix_nanoseconds() -> None:
    span = build_generation_span(build_trace())
    again = build_generation_span(build_trace())
    uuid_span = build_generation_span(
        build_trace().model_copy(update={"trace_id": CorrelationId(UUID_TRACE_ID)})
    )

    trace_hex, span_hex = str(span["traceId"]), str(span["spanId"])
    assert len(trace_hex) == 32 and int(trace_hex, 16) > 0
    assert len(span_hex) == 16 and int(span_hex, 16) > 0
    assert (again["traceId"], again["spanId"]) == (trace_hex, span_hex)
    # A UUID keeps its digits, so the journal's id is found in Langfuse.
    assert uuid_span["traceId"] == "0f8fad5bd9cb469fa16570867728950e"
    assert otel_trace_id("trace-2") != trace_hex
    # Started at 1_790_000_000 s, 250 ms long.
    assert span["startTimeUnixNano"] == "1790000000000000000"
    assert span["endTimeUnixNano"] == "1790000000250000000"


def test_a_failed_call_is_an_error_with_its_error_name_only() -> None:
    trace = build_trace().model_copy(
        update={
            "error": JobErrorText("ExternalServiceError"),
            "started_at": Microseconds(1_790_000_000_000_001),
            "elapsed": ElapsedMilliseconds(0),
        }
    )

    span = build_generation_span(trace)
    attributes = attributes_of(span)

    assert span["status"] == {"code": 2}
    assert attributes["langfuse.observation.level"] == "ERROR"
    assert attributes["langfuse.observation.status_message"] == "ExternalServiceError"
    assert span["startTimeUnixNano"] == span["endTimeUnixNano"] == "1790000000000001000"


def test_texts_tools_session_and_correlation_are_mapped_when_present() -> None:
    conversation_id = ConversationId()
    trace = build_trace().model_copy(
        update={
            "input_text": MessageText("Есть столик на 4?"),
            "output_text": MessageText('{"not": "json"}'),
            "called_tools": [AssistantToolName.GET_PRICE],
            "conversation_id": conversation_id,
            "request_id": RequestId("request-0000-0001"),
            "request_trace_id": TraceId("4bf92f3577b34da6a3ce929d0e0e4736"),
        }
    )

    attributes = attributes_of(build_generation_span(trace))

    assert attributes["langfuse.session.id"] == str(conversation_id)
    # JSON strings, so a text that looks like JSON stays a text.
    assert json.loads(attributes["langfuse.observation.input"]) == "Есть столик на 4?"
    assert json.loads(attributes["langfuse.observation.output"]) == '{"not": "json"}'
    assert json.loads(attributes["langfuse.observation.metadata.called_tools"]) == [
        "get_price"
    ]
    for level in ("trace", "observation"):
        prefix = f"langfuse.{level}.metadata."
        assert attributes[prefix + "request_id"] == "request-0000-0001"
        assert attributes[prefix + "trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
        assert attributes[prefix + "conversation_id"] == str(conversation_id)


def test_the_client_posts_one_otlp_request_with_auth_and_version_header() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    client = langfuse_client(httpx.MockTransport(handle))
    span = build_generation_span(build_trace())
    client.ingest([span])
    client.ingest([])

    [request] = requests
    assert request.method == "POST"
    assert str(request.url) == "https://cloud.langfuse.com/api/public/otel/v1/traces"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["x-langfuse-ingestion-version"] == "4"
    credentials = base64.b64decode(request.headers["authorization"].split()[1])
    assert credentials == b"pk-lf-test-0000:sk-lf-test-0000"
    [resource_spans] = json.loads(request.content)["resourceSpans"]
    [scope_spans] = resource_spans["scopeSpans"]
    assert scope_spans["scope"] == {"name": "assistant-workshop.quality-journal"}
    assert scope_spans["spans"] == [span]


@pytest.mark.parametrize("failure", ["status", "network"])
def test_client_failures_are_external_service_errors(failure: str) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if failure == "network":
            raise httpx.ConnectError("refused", request=request)

        return httpx.Response(401, json={"message": "Invalid credentials"})

    with pytest.raises(ExternalServiceError, match="Langfuse ingestion"):
        langfuse_client(httpx.MockTransport(handle)).ingest(
            [build_generation_span(build_trace())]
        )


def test_the_facilitator_batches_and_drops_what_cannot_be_sent() -> None:
    batches: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        batches.append(len(body["resourceSpans"][0]["scopeSpans"][0]["spans"]))
        return httpx.Response(200, json={})

    facilitator = LangfuseTraceFacilitator(langfuse_client(httpx.MockTransport(handle)))
    for _ in range(60):
        facilitator.record_generation(build_trace())

    facilitator.flush()

    assert batches == [50, 10]
    assert facilitator.buffered_span_count == 0

    failing = LangfuseTraceFacilitator(
        langfuse_client(httpx.MockTransport(lambda request: httpx.Response(500)))
    )
    failing.record_generation(build_trace())
    failing.flush()  # logged, never raised

    assert failing.buffered_span_count == 0


def test_the_buffer_keeps_the_newest_spans_when_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.facilitators.observability.langfuse_trace_facilitator.MAX_BUFFERED_SPANS",
        2,
    )
    facilitator = LangfuseTraceFacilitator(
        langfuse_client(httpx.MockTransport(lambda request: httpx.Response(200)))
    )
    for _ in range(3):
        facilitator.record_generation(build_trace())

    assert facilitator.buffered_span_count == 2


def test_a_trace_that_cannot_be_encoded_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(trace: LlmGenerationTrace) -> dict[str, object]:
        raise ValueError(f"cannot encode {trace.trace_id}")

    monkeypatch.setattr(
        "app.facilitators.observability.langfuse_trace_facilitator.build_generation_span",
        broken,
    )
    facilitator = LangfuseTraceFacilitator(
        langfuse_client(httpx.MockTransport(lambda request: httpx.Response(200)))
    )

    facilitator.record_generation(build_trace())

    assert facilitator.buffered_span_count == 0
