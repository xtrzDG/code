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
    read_object,
    read_objects,
    read_text,
)

TRACES_PATH: str = "/api/public/traces"
OBSERVATIONS_PATH: str = "/api/public/v2/observations"
# The Observations API v2 answers at most 1000 per page.
PAGE_SIZE: int = 1000
# A session older than its trace pages is a bug, not data: stop there.
MAX_PAGES: int = 1000
REQUEST_TIMEOUT_SECONDS: float = 10.0


class LangfuseTracesClient(LangfuseTraceClientContract):
    """
    The trace endpoints of the Langfuse public API (HTTP basic auth with
    the project's public and secret key): GET /api/public/v2/observations
    filtered by `sessionId` (cursor pages of the core fields, whose
    `traceId` names the trace; Langfuse retired the trace listing) and
    DELETE /api/public/traces with `traceIds`, which Langfuse carries out
    in the background.
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
        seen: set[CorrelationId] = set()
        cursor: str | None = None
        for _ in range(MAX_PAGES):
            params: dict[str, str] = {
                "sessionId": str(session_id),
                "limit": str(PAGE_SIZE),
                "fields": "core",
            }
            if cursor is not None:
                params["cursor"] = cursor

            body: JsonObject = self._send("GET", OBSERVATIONS_PATH, params=params)
            # A trace's observations share its id: each trace once, in order.
            for trace_id in read_trace_ids(body):
                if trace_id not in seen:
                    seen.add(trace_id)
                    trace_ids.append(trace_id)

            cursor = read_next_cursor(body)
            if cursor is None:
                break

        return trace_ids

    def delete_traces(self, trace_ids: Sequence[CorrelationId]) -> None:
        if not trace_ids:
            return

        self._send(
            "DELETE",
            TRACES_PATH,
            json={"traceIds": [str(trace) for trace in trace_ids]},
        )

    def _send(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> JsonObject:
        try:
            response: httpx.Response = self._http_client.request(
                method, path, params=params, json=json
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
    """
    The trace ids of one page of observations (`data[].traceId`); entries
    without one are skipped.
    """

    return [
        CorrelationId(trace_id)
        for entry in read_objects(body, "data")
        if (trace_id := read_text(entry, "traceId"))
    ]


def read_next_cursor(body: JsonObject) -> str | None:
    """`meta.cursor`, the next page's cursor; None on the last page."""

    meta: JsonObject = read_object(body, "meta") or {}
    return read_text(meta, "cursor")
