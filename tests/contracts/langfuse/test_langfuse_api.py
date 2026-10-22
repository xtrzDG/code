"""
The Langfuse public API as the quality journal uses it: the OTLP/JSON
export the facilitator sends to POST /api/public/otel/v1/traces (a span
with content, error and every metadata key) and the trace deletion match
Langfuse's specification with every object closed; the documented answers
(an accepted export, a page of observations) match it and are read.

Langfuse's OpenAPI document leaves the span's ids, times and status
untyped, so the export is also held to the OTLP/JSON encoding
(opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding) by the small
schema below: hex ids of 16 and 8 bytes, nanosecond times as decimal
strings, a status code of the OTLP enum.
"""

from typing import Any

from typed_time_provider import Microseconds

from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.langfuse.langfuse_traces_client import LangfuseTracesClient
from app.facilitators.observability.langfuse_trace_facilitator import (
    LangfuseTraceFacilitator,
)
from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
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
    TraceSessionId,
)
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import (
    assert_inbound,
    assert_outbound,
    schema_validator,
)

SPEC: str = "langfuse_public_api.json"
HOST = PublicBaseUrl("https://cloud.langfuse.com")
PUBLIC_KEY = PlatformIdentifier("pk-lf-test-0000")
SECRET_KEY = PlatformSecret("sk-lf-test-0000")
UNIX_NANOSECONDS: dict[str, str] = {"type": "string", "pattern": "^[0-9]{1,20}$"}
OTLP_SPAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "traceId",
        "spanId",
        "name",
        "kind",
        "startTimeUnixNano",
        "endTimeUnixNano",
        "attributes",
    ],
    "properties": {
        "traceId": {"type": "string", "pattern": "^(?!0{32})[0-9a-f]{32}$"},
        "spanId": {"type": "string", "pattern": "^(?!0{16})[0-9a-f]{16}$"},
        "parentSpanId": {"type": "string", "pattern": "^(?!0{16})[0-9a-f]{16}$"},
        "kind": {"enum": [0, 1, 2, 3, 4, 5]},
        "startTimeUnixNano": UNIX_NANOSECONDS,
        "endTimeUnixNano": UNIX_NANOSECONDS,
        "status": {
            "type": "object",
            "properties": {"code": {"enum": [0, 1, 2]}, "message": {"type": "string"}},
            "additionalProperties": False,
        },
        "attributes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["key", "value"],
                "properties": {
                    "key": {"type": "string", "minLength": 1},
                    "value": {"type": "object", "minProperties": 1, "maxProperties": 1},
                },
            },
        },
    },
}


def full_trace() -> LlmGenerationTrace:
    return LlmGenerationTrace(
        trace_id=CorrelationId("0f8fad5b-d9cb-469f-a165-70867728950e"),
        model_id=LlmModelId("gpt-5-mini"),
        effort=LlmEffort.LOW,
        offered_tools=[AssistantToolName.GET_PRICE],
        called_tools=[AssistantToolName.GET_PRICE],
        stop_reason=LlmStopReason.END_TURN,
        input_tokens=LlmTokenCount(1500),
        output_tokens=LlmTokenCount(60),
        started_at=Microseconds(1_790_845_200_000_000),
        elapsed=ElapsedMilliseconds(1500),
        input_text=MessageText("რა ღირს ხაჭაპური?"),
        output_text=MessageText("აჭარული ხაჭაპური ღირს 18 ₾."),
        error=JobErrorText("OpenAI did not answer in time."),
        business_id=BusinessId(),
        contact_id=ContactId(),
        conversation_id=ConversationId(),
        request_id=RequestId("request-0000-0001"),
        request_trace_id=TraceId("4bf92f3577b34da6a3ce929d0e0e4736"),
    )


def test_documented_answers_match_the_specification() -> None:
    assert_inbound(
        load_json_fixture("langfuse", "otel_traces_accepted.json"),
        SPEC,
        "response:otel.traces",
    )
    assert_inbound(
        load_json_fixture("langfuse", "observations_page.json"),
        SPEC,
        "response:observations.list",
    )


def test_otel_export_matches_the_specification_and_otlp_json() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/api/public/otel/v1/traces$",
        load_json_fixture("langfuse", "otel_traces_accepted.json"),
    )
    facilitator = LangfuseTraceFacilitator(
        LangfuseIngestionClient(HOST, PUBLIC_KEY, SECRET_KEY, transport.build())
    )

    facilitator.record_generation(full_trace())
    facilitator.record_generation(
        full_trace().model_copy(update={"error": None, "input_text": None})
    )
    facilitator.flush()

    [request] = transport.requests
    assert request.headers["x-langfuse-ingestion-version"] == "4"
    body: dict[str, Any] = request.json()
    assert_outbound(body, SPEC, "request:otel.traces")
    spans: list[dict[str, Any]] = body["resourceSpans"][0]["scopeSpans"][0]["spans"]
    span_validator = schema_validator(OTLP_SPAN_SCHEMA)
    for span in spans:
        span_validator.validate(span)

    assert [span["status"]["code"] for span in spans if "status" in span] == [2]
    assert facilitator.buffered_span_count == 0


def test_trace_listing_and_deletion_match_the_specification() -> None:
    transport = RecordingTransport()
    transport.respond(
        "GET",
        r"/api/public/v2/observations$",
        load_json_fixture("langfuse", "observations_page.json"),
    )
    transport.respond("DELETE", r"/api/public/traces$", {"message": "Traces deleted"})
    traces = LangfuseTracesClient(HOST, PUBLIC_KEY, SECRET_KEY, transport.build())

    trace_ids = traces.list_session_trace_ids(TraceSessionId("conversation_0000-0001"))
    traces.delete_traces(trace_ids)

    assert trace_ids == [
        "0000aaaa0000aaaa0000aaaa0000aaa1",
        "0000aaaa0000aaaa0000aaaa0000aaa2",
    ]
    deletion = transport.requests[-1]
    assert_outbound(deletion.json(), SPEC, "request:traces.delete")
