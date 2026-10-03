import logging
import threading
import uuid
from datetime import UTC, datetime

from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.contracts.observability import LlmTraceFacilitatorContract
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.exceptions.base_exception import ApplicationError

LOGGER: logging.Logger = logging.getLogger(__name__)
MAX_BUFFERED_EVENTS: int = 1000
FLUSH_BATCH_SIZE: int = 50


class LangfuseTraceFacilitator(LlmTraceFacilitatorContract):
    """
    Buffers generation traces and sends them to Langfuse in batches.

    Tracing must never slow down or break a customer reply: recording only
    appends to a bounded buffer, and delivery errors are logged and dropped.
    Call `flush` from a background job or at shutdown.
    """

    def __init__(self, client: LangfuseIngestionClient) -> None:
        self._client: LangfuseIngestionClient = client
        self._buffer: list[dict[str, object]] = []
        self._lock: threading.Lock = threading.Lock()

    def record_generation(self, trace: LlmGenerationTrace) -> None:
        try:
            events: list[dict[str, object]] = build_generation_events(trace)
        except (TypeError, ValueError) as error:
            LOGGER.warning("Could not build a Langfuse event: %s", error)
            return

        with self._lock:
            overflow: int = len(self._buffer) + len(events) - MAX_BUFFERED_EVENTS
            if overflow > 0:
                del self._buffer[:overflow]
                LOGGER.warning("Langfuse buffer full; dropped %d events.", overflow)

            self._buffer.extend(events)

    def flush(self) -> None:
        while True:
            with self._lock:
                batch: list[dict[str, object]] = self._buffer[:FLUSH_BATCH_SIZE]
                del self._buffer[:FLUSH_BATCH_SIZE]

            if not batch:
                return

            try:
                self._client.ingest(batch)
            except ApplicationError as error:
                LOGGER.warning("Langfuse batch dropped: %s", error)
                return

    @property
    def buffered_event_count(self) -> int:
        with self._lock:
            return len(self._buffer)


def build_generation_events(trace: LlmGenerationTrace) -> list[dict[str, object]]:
    """Langfuse ingestion events (trace-create + generation-create) for a call."""

    start_time: str = format_timestamp(int(trace.started_at))
    end_time: str = format_timestamp(int(trace.started_at) + int(trace.elapsed) * 1000)
    metadata: dict[str, object] = {
        "effort": str(trace.effort),
        "offered_tools": [str(tool) for tool in trace.offered_tools],
        "called_tools": [str(tool) for tool in trace.called_tools],
        "stop_reason": None if trace.stop_reason is None else str(trace.stop_reason),
        "elapsed_ms": int(trace.elapsed),
    }
    generation_body: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "traceId": str(trace.trace_id),
        "name": "assistant_reply",
        "model": str(trace.model_id),
        "startTime": start_time,
        "endTime": end_time,
        "usage": {
            "input": int(trace.input_tokens),
            "output": int(trace.output_tokens),
            "unit": "TOKENS",
        },
        "metadata": metadata,
        "level": "DEFAULT" if trace.error is None else "ERROR",
    }
    if trace.input_text is not None:
        generation_body["input"] = str(trace.input_text)

    if trace.output_text is not None:
        generation_body["output"] = str(trace.output_text)

    if trace.error is not None:
        generation_body["statusMessage"] = str(trace.error)

    return [
        {
            "id": str(uuid.uuid4()),
            "timestamp": start_time,
            "type": "trace-create",
            "body": {
                "id": str(trace.trace_id),
                "name": "assistant_reply",
                "metadata": {"model": str(trace.model_id)},
            },
        },
        {
            "id": str(uuid.uuid4()),
            "timestamp": end_time,
            "type": "generation-create",
            "body": generation_body,
        },
    ]


def format_timestamp(unix_microseconds: int) -> str:
    moment: datetime = datetime.fromtimestamp(unix_microseconds / 1_000_000, tz=UTC)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")
