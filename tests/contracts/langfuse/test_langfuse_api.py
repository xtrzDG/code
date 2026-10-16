"""
The Langfuse public API as the quality journal uses it: the ingestion
batch the facilitator sends (a trace and its generation, content and an
error included) and the trace deletion match Langfuse's specification with
every object closed; the documented answers (a 207 multi-status, a page of
traces) match it and are read.
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
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds
from app.schemas.typings.platform.strings import (
    CorrelationId,
    JobErrorText,
    PlatformIdentifier,
    PlatformSecret,
    TraceSessionId,
)
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "langfuse_public_api.json"
HOST = PublicBaseUrl("https://cloud.langfuse.com")
PUBLIC_KEY = PlatformIdentifier("pk-lf-test-0000")
SECRET_KEY = PlatformSecret("sk-lf-test-0000")


def full_trace() -> LlmGenerationTrace:
    return LlmGenerationTrace(
        trace_id=CorrelationId("trace-0000-0001"),
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
    )


def test_documented_answers_match_the_specification() -> None:
    assert_inbound(
        load_json_fixture("langfuse", "ingestion_multi_status.json"),
        SPEC,
        "response:ingestion",
    )
    assert_inbound(
        load_json_fixture("langfuse", "traces_page.json"), SPEC, "response:traces.list"
    )


def test_ingestion_batch_matches_the_specification() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/api/public/ingestion$",
        load_json_fixture("langfuse", "ingestion_multi_status.json"),
        207,
    )
    facilitator = LangfuseTraceFacilitator(
        LangfuseIngestionClient(HOST, PUBLIC_KEY, SECRET_KEY, transport.build())
    )

    facilitator.record_generation(full_trace())
    facilitator.flush()

    [request] = transport.requests
    body: dict[str, Any] = request.json()
    assert_outbound(body, SPEC, "request:ingestion")
    assert [event["type"] for event in body["batch"]] == [
        "trace-create",
        "generation-create",
    ]
    # A partial failure Langfuse reports in the 207 is not retried.
    assert facilitator.buffered_event_count == 0


def test_trace_listing_and_deletion_match_the_specification() -> None:
    transport = RecordingTransport()
    transport.respond(
        "GET", r"/api/public/traces$", load_json_fixture("langfuse", "traces_page.json")
    )
    transport.respond("DELETE", r"/api/public/traces$", {"message": "Traces deleted"})
    traces = LangfuseTracesClient(HOST, PUBLIC_KEY, SECRET_KEY, transport.build())

    trace_ids = traces.list_session_trace_ids(TraceSessionId("conversation_0000-0001"))
    traces.delete_traces(trace_ids)

    assert trace_ids == ["trace-0000-0001", "trace-0000-0002"]
    deletion = transport.requests[-1]
    assert_outbound(deletion.json(), SPEC, "request:traces.delete")
