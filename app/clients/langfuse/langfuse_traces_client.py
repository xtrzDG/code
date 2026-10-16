from collections.abc import Sequence

import httpx

from app.contracts.channel_clients import JsonObject
from app.contracts.processor_erasure import LangfuseTraceClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import (
    CorrelationId,
    PlatformIdentifier,
    PlatformSecret,
    TraceSessionId,
)
from app.utilities.channels.json_values import (
    parse_json_object,
    read_integer,
    read_object,
    read_objects,
    read_text,
)

TRACES_PATH: str = "/api/public/traces"
PAGE_SIZE: int = 100
# A session older than its trace pages is a bug, not data: stop there.
MAX_PAGES: int = 1000
REQUEST_TIMEOUT_SECONDS: float = 10.0


class LangfuseTracesClient(LangfuseTraceClientContract):
    """
    The trace endpoints of the Langfuse public API (HTTP basic auth with
    the project's public and secret key): GET /api/public/traces filtered
    by `sessionId` (pages of ids only, `fields=core`) and DELETE
    /api/public/traces with `traceIds`, which Langfuse carries out in the
    background.
    """

    def __init__(
        self,
        host: PublicBaseUrl,
        public_key: PlatformIdentifier,
        secret_key: PlatformSecret,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=str(host).rstrip("/"),
            auth=(str(public_key), str(secret_key)),
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def list_session_trace_ids(self, session_id: TraceSessionId) -> list[CorrelationId]:
        trace_ids: list[CorrelationId] = []
        for page in range(1, MAX_PAGES + 1):
            body: JsonObject = self._send(
                "GET",
                params={
                    "sessionId": str(session_id),
                    "page": str(page),
                    "limit": str(PAGE_SIZE),
                    "fields": "core",
                },
            )
            trace_ids.extend(read_trace_ids(body))
            if page >= read_total_pages(body):
                break

        return trace_ids

    def delete_traces(self, trace_ids: Sequence[CorrelationId]) -> None:
        if not trace_ids:
            return

        self._send("DELETE", json={"traceIds": [str(trace) for trace in trace_ids]})

    def _send(
        self,
        method: str,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> JsonObject:
        try:
            response: httpx.Response = self._http_client.request(
                method, TRACES_PATH, params=params, json=json
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                f"Langfuse traces request failed: {type(error).__name__}."
            ) from error

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Langfuse traces request returned HTTP {response.status_code}."
            )

        return parse_json_object(response.content) or {}


def read_trace_ids(body: JsonObject) -> list[CorrelationId]:
    """The ids of one page (`data[].id`); entries without one are skipped."""

    return [
        CorrelationId(trace_id)
        for entry in read_objects(body, "data")
        if (trace_id := read_text(entry, "id"))
    ]


def read_total_pages(body: JsonObject) -> int:
    """`meta.totalPages`; 1 when the answer has none (one page)."""

    meta: JsonObject = read_object(body, "meta") or {}
    total_pages: int | None = read_integer(meta, "totalPages")
    return 1 if total_pages is None else total_pages
