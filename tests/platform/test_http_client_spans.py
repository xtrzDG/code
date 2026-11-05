"""
Calls to providers over httpx are client spans (with OpenTelemetry on):
`METHOD host`, the path as a template, the status; no ids, tokens or
query, and no trace header sent to the provider.
"""

from collections.abc import Iterator

import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind as OtelSpanKind
from opentelemetry.trace import StatusCode

from app.utilities.observability.tracing.http_client_spans import (
    install_http_client_spans,
    path_template,
)
from app.utilities.observability.tracing.open_telemetry_span_tracer import (
    OpenTelemetrySpanTracer,
)
from app.utilities.observability.tracing.span_tracer import NO_SPAN_TRACER

BOT_PATH: str = "/bot7770001:AAHbusiness_bot_token_for_e2e_tests_0123/sendMessage"


@pytest.fixture
def exporter(monkeypatch: pytest.MonkeyPatch) -> Iterator[InMemorySpanExporter]:
    # The wrapper is process-wide: put the real send back after the test.
    monkeypatch.setattr(httpx.Client, "send", httpx.Client.send)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    assert install_http_client_spans(
        OpenTelemetrySpanTracer(provider.get_tracer("tests"))
    )
    yield exporter
    provider.shutdown()


def test_path_templates_hide_ids_tokens_and_addresses() -> None:
    assert path_template(httpx.URL(f"https://api.telegram.org{BOT_PATH}")) == (
        "/*/sendMessage"
    )
    assert (
        path_template(
            httpx.URL("https://graph.facebook.com/v21.0/1155/messages?access_token=x")
        )
        == "/v21.0/*/messages"
    )
    assert path_template(httpx.URL("https://api.example.com/users/a@b.ge")) == (
        "/users/*"
    )
    assert path_template(httpx.URL("https://api.anthropic.com/v1/messages")) == (
        "/v1/messages"
    )


def test_a_provider_call_is_a_client_span_without_secrets(
    exporter: InMemorySpanExporter,
) -> None:
    seen_headers: list[httpx.Headers] = []

    def provider(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        return httpx.Response(503 if "fail" in request.url.path else 200)

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        client.post(f"https://api.telegram.org{BOT_PATH}?chat_id=9001")
        client.get("https://api.example.com/fail")

    sent, failed = exporter.get_finished_spans()
    assert sent.name == "POST api.telegram.org"
    assert sent.kind is OtelSpanKind.CLIENT
    assert sent.attributes is not None
    assert sent.attributes["url.template"] == "/*/sendMessage"
    assert sent.attributes["http.response.status_code"] == 200
    assert "AAH" not in str(dict(sent.attributes)) + sent.name
    assert "9001" not in str(dict(sent.attributes))
    assert failed.status.status_code is StatusCode.ERROR
    assert all("traceparent" not in headers for headers in seen_headers)


def test_without_a_recording_tracer_nothing_is_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx.Client, "send", httpx.Client.send)
    real_send = httpx.Client.send

    assert not install_http_client_spans(NO_SPAN_TRACER)
    assert httpx.Client.send is real_send
