"""
A model call as an OpenTelemetry span in OTLP/JSON for Langfuse
(`POST /api/public/otel/v1/traces`, langfuse.com/integrations/native/
opentelemetry, "Property Mapping").

One call is one trace with one root span of observation type `generation`:
the trace-level attributes (`langfuse.trace.*`, `langfuse.session.id`) on
that span name the trace and its session, the observation attributes
(`langfuse.observation.*`) carry the model, usage, level and texts. The
span carries exactly what the legacy `trace-create` and `generation-create`
events carried, nothing more: no user id, no contact details.
"""

import hashlib
import json
import uuid

from app.schemas.dto.observability import LlmGenerationTrace

GENERATION_NAME: str = "assistant_reply"
SPAN_KIND_INTERNAL: int = 1
STATUS_CODE_ERROR: int = 2
NANOSECONDS_PER_MICROSECOND: int = 1000
MICROSECONDS_PER_MILLISECOND: int = 1000
TRACE_ID_HEX_DIGITS: int = 32
SPAN_ID_HEX_DIGITS: int = 16

type OtlpAttribute = dict[str, object]


def build_generation_span(trace: LlmGenerationTrace) -> dict[str, object]:
    """The OTLP/JSON span (one `generation` observation) of one model call."""

    trace_hex: str = otel_trace_id(str(trace.trace_id))
    started_us: int = int(trace.started_at)
    ended_us: int = started_us + int(trace.elapsed) * MICROSECONDS_PER_MILLISECOND
    span: dict[str, object] = {
        "traceId": trace_hex,
        "spanId": otel_span_id(trace_hex, "generation"),
        "name": GENERATION_NAME,
        "kind": SPAN_KIND_INTERNAL,
        "startTimeUnixNano": str(started_us * NANOSECONDS_PER_MICROSECOND),
        "endTimeUnixNano": str(ended_us * NANOSECONDS_PER_MICROSECOND),
        "attributes": [
            otlp_attribute(key, value)
            for key, value in generation_attributes(trace).items()
        ],
    }
    if trace.error is not None:
        span["status"] = {"code": STATUS_CODE_ERROR}

    return span


def generation_attributes(trace: LlmGenerationTrace) -> dict[str, str]:
    """Langfuse's attributes of the call's trace and generation, by key."""

    owners: dict[str, str] = trace_owners(trace)
    correlation: dict[str, str] = request_correlation(trace)
    input_tokens: int = int(trace.input_tokens)
    output_tokens: int = int(trace.output_tokens)
    attributes: dict[str, str] = {
        "langfuse.observation.type": "generation",
        "langfuse.trace.name": GENERATION_NAME,
        "langfuse.observation.model.name": str(trace.model_id),
        # Langfuse's usage keeps the total next to its parts.
        "langfuse.observation.usage_details": json.dumps(
            {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            }
        ),
        "langfuse.observation.level": "DEFAULT" if trace.error is None else "ERROR",
    }
    if trace.conversation_id is not None:
        attributes["langfuse.session.id"] = str(trace.conversation_id)

    trace_metadata: dict[str, str] = {
        "model": str(trace.model_id),
        **owners,
        **correlation,
    }
    observation_metadata: dict[str, str] = {
        **owners,
        **correlation,
        "effort": str(trace.effort),
        "offered_tools": json.dumps([str(tool) for tool in trace.offered_tools]),
        "called_tools": json.dumps([str(tool) for tool in trace.called_tools]),
        "elapsed_ms": str(int(trace.elapsed)),
    }
    if trace.stop_reason is not None:
        observation_metadata["stop_reason"] = str(trace.stop_reason)

    attributes.update(
        {
            f"langfuse.trace.metadata.{key}": value
            for key, value in trace_metadata.items()
        }
    )
    attributes.update(
        {
            f"langfuse.observation.metadata.{key}": value
            for key, value in observation_metadata.items()
        }
    )
    # Texts as JSON strings, so Langfuse keeps them as text whatever they hold.
    if trace.input_text is not None:
        attributes["langfuse.observation.input"] = json.dumps(
            str(trace.input_text), ensure_ascii=False
        )

    if trace.output_text is not None:
        attributes["langfuse.observation.output"] = json.dumps(
            str(trace.output_text), ensure_ascii=False
        )

    if trace.error is not None:
        attributes["langfuse.observation.status_message"] = str(trace.error)

    return attributes


def trace_owners(trace: LlmGenerationTrace) -> dict[str, str]:
    """
    The business, contact and conversation the call answered (those known):
    the keys erasure and retention find a trace by. The conversation is
    also the trace's session.
    """

    owners: dict[str, str] = {}
    if trace.business_id is not None:
        owners["business_id"] = str(trace.business_id)

    if trace.contact_id is not None:
        owners["contact_id"] = str(trace.contact_id)

    if trace.conversation_id is not None:
        owners["conversation_id"] = str(trace.conversation_id)

    return owners


def request_correlation(trace: LlmGenerationTrace) -> dict[str, str]:
    """The request id and trace id that find the call's logs and spans."""

    correlation: dict[str, str] = {}
    if trace.request_id is not None:
        correlation["request_id"] = str(trace.request_id)

    if trace.request_trace_id is not None:
        correlation["trace_id"] = str(trace.request_trace_id)

    return correlation


def otel_trace_id(correlation_id: str) -> str:
    """
    The 16-byte OTel trace id (32 hex digits) of a journal trace: a UUID's
    own digits, any other id hashed. Langfuse names the trace by it.
    """

    try:
        return uuid.UUID(correlation_id).hex
    except ValueError:
        digest: str = hashlib.sha256(correlation_id.encode("utf-8")).hexdigest()
        return digest[:TRACE_ID_HEX_DIGITS]


def otel_span_id(trace_hex: str, role: str) -> str:
    """The 8-byte span id (16 hex digits) of one span of the trace, stable."""

    digest: str = hashlib.sha256(f"{trace_hex}:{role}".encode()).hexdigest()
    return digest[:SPAN_ID_HEX_DIGITS]


def otlp_attribute(key: str, value: str) -> OtlpAttribute:
    """
    One OTLP `KeyValue` with a string `AnyValue`: Langfuse reads its
    metadata, usage and texts as (JSON) strings.
    """

    return {"key": key, "value": {"stringValue": value}}
