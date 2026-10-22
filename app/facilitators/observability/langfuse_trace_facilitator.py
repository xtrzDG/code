import logging
import threading

from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.contracts.observability import LlmTraceFacilitatorContract
from app.facilitators.observability.langfuse_otel_spans import build_generation_span
from app.schemas.dto.observability import LlmGenerationTrace
from app.schemas.exceptions.base_exception import ApplicationError

LOGGER: logging.Logger = logging.getLogger(__name__)
MAX_BUFFERED_SPANS: int = 1000
FLUSH_BATCH_SIZE: int = 50


class LangfuseTraceFacilitator(LlmTraceFacilitatorContract):
    """
    Buffers generation traces as OpenTelemetry spans and sends them to
    Langfuse's OTLP endpoint in batches.

    Tracing must never slow down or break a customer reply: recording only
    appends to a bounded buffer, and delivery errors are logged and dropped.
    Call `flush` from a background job or at shutdown. A trace carries the
    ids of its business, contact and conversation as metadata and the
    conversation as its session (`langfuse.session.id`), so
    `LangfuseTraceErasureAdapter` can delete a conversation's traces; the
    request id and the distributed trace id find the call's log lines and
    spans.
    """

    def __init__(self, client: LangfuseIngestionClient) -> None:
        self._client: LangfuseIngestionClient = client
        self._buffer: list[dict[str, object]] = []
        self._lock: threading.Lock = threading.Lock()

    def record_generation(self, trace: LlmGenerationTrace) -> None:
        try:
            span: dict[str, object] = build_generation_span(trace)
        except (TypeError, ValueError) as error:
            LOGGER.warning("Could not build a Langfuse span: %s", error)
            return

        with self._lock:
            overflow: int = len(self._buffer) + 1 - MAX_BUFFERED_SPANS
            if overflow > 0:
                del self._buffer[:overflow]
                LOGGER.warning("Langfuse buffer full; dropped %d spans.", overflow)

            self._buffer.append(span)

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
    def buffered_span_count(self) -> int:
        with self._lock:
            return len(self._buffer)
