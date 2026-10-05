"""The trace endpoints of the Langfuse public API, over a fake transport."""

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
    "1": {
        "data": [{"id": "trace-1"}, {"id": "trace-2"}, {"name": "no id"}],
        "meta": {"page": 1, "limit": 100, "totalItems": 3, "totalPages": 2},
    },
    "2": {"data": [{"id": "trace-3"}], "meta": {"page": 2, "totalPages": 2}},
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
        return httpx.Response(200, json=PAGES[request.url.params["page"]])

    trace_ids = client(httpx.MockTransport(answer)).list_session_trace_ids(
        TraceSessionId("conversation_1")
    )

    assert trace_ids == ["trace-1", "trace-2", "trace-3"]
    assert [request.url.path for request in requests] == ["/api/public/traces"] * 2
    params = requests[0].url.params
    assert (params["sessionId"], params["fields"], params["limit"]) == (
        "conversation_1",
        "core",
        "100",
    )
    assert requests[0].headers["authorization"].startswith("Basic ")


def test_an_answer_without_paging_is_one_page() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"data": [{"id": "only"}]})

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
