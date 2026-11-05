"""
The trace endpoints of the Langfuse public API, over a fake transport: a
session's traces are listed through the Observations API v2 (cursor pages)
and deleted by id.
"""

import json

import httpx
import pytest

from app.clients.langfuse.langfuse_traces_client import LangfuseTracesClient
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import (
    CorrelationId,
    PlatformIdentifier,
    PlatformSecret,
    TraceSessionId,
)

PAGES: dict[str, dict[str, object]] = {
    "": {
        "data": [
            {"id": "observation-1", "traceId": "trace-1"},
            {"id": "observation-2", "traceId": "trace-2"},
            {"id": "observation-3", "traceId": "trace-1"},
            {"id": "observation-4"},
        ],
        "meta": {"cursor": "cursor-0000-0002"},
    },
    "cursor-0000-0002": {
        "data": [{"id": "observation-5", "traceId": "trace-3"}],
        "meta": {},
    },
}


def client(handler: httpx.MockTransport) -> LangfuseTracesClient:
    return LangfuseTracesClient(
        host=PublicBaseUrl("https://cloud.langfuse.com/"),
        public_key=PlatformIdentifier("pk-lf-test-0000"),
        secret_key=PlatformSecret("sk-lf-test-0000"),
        transport=handler,
    )


def test_every_page_of_a_session_is_read_with_ids_only() -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=PAGES[request.url.params.get("cursor", "")])

    trace_ids = client(httpx.MockTransport(answer)).list_session_trace_ids(
        TraceSessionId("conversation_1")
    )

    # Each trace once, though several of its observations are listed.
    assert trace_ids == ["trace-1", "trace-2", "trace-3"]
    assert [request.url.path for request in requests] == [
        "/api/public/v2/observations"
    ] * 2
    params = requests[0].url.params
    assert (params["sessionId"], params["fields"], params["limit"]) == (
        "conversation_1",
        "core",
        "1000",
    )
    assert "cursor" not in params
    assert requests[1].url.params["cursor"] == "cursor-0000-0002"
    assert requests[0].headers["authorization"].startswith("Basic ")


def test_an_answer_without_paging_is_one_page() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"data": [{"traceId": "only"}]})

    assert client(httpx.MockTransport(answer)).list_session_trace_ids(
        TraceSessionId("c")
    ) == ["only"]


def test_traces_are_deleted_by_id_and_nothing_is_sent_for_none() -> None:
    bodies: list[dict[str, object]] = []

    def answer(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": "Traces deleted"})

    traces = client(httpx.MockTransport(answer))
    traces.delete_traces([CorrelationId("trace-1"), CorrelationId("trace-2")])
    traces.delete_traces([])

    assert bodies == [{"traceIds": ["trace-1", "trace-2"]}]


@pytest.mark.parametrize("failure", ["status", "network"])
def test_failures_are_external_service_errors(failure: str) -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if failure == "network":
            raise httpx.ConnectError("refused", request=request)

        return httpx.Response(503, json={"error": "unavailable"})

    with pytest.raises(ExternalServiceError, match="Langfuse traces request"):
        client(httpx.MockTransport(answer)).delete_traces([CorrelationId("t")])
