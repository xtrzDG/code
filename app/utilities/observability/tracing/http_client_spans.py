"""
Spans of the calls this process makes to providers over httpx (Telegram,
Meta, the model APIs, Twilio...), for OpenTelemetry: one client span per
request named `METHOD host`, with the path as a template (segments with
digits, tokens or addresses become `*`, so bot tokens and ids never leave),
the method and the status. No trace headers go to providers: their side of
the trace is not ours, and a header is one more thing a provider stores.

httpx has no hook for every client, so `httpx.Client.send` is wrapped once
per process (the way Sentry's HttpxIntegration does it for its own spans).
"""

import re
import threading
from collections.abc import Callable

import httpx

from app.schemas.constants.telemetry import SpanKind
from app.utilities.observability.tracing.span_tracer import SpanTracer

MASKED_SEGMENT: str = "*"
# A path segment that may identify someone or carry a secret: digits, an
# address, a token-like run, or simply a long one.
IDENTIFYING_SEGMENT: re.Pattern[str] = re.compile(r"[0-9@:=%+]|^[A-Za-z0-9_-]{24,}$")
# An API version (`v1`, `v21.0`) names no one and is kept.
VERSION_SEGMENT: re.Pattern[str] = re.compile(r"^v[0-9]+(\.[0-9]+)*$")
LONGEST_KEPT_SEGMENT: int = 40
SERVER_ERROR_STATUS: int = 500
WRAPPED_MARK: str = "_workshop_spans"

type Send = Callable[..., httpx.Response]

_install_lock: threading.Lock = threading.Lock()


def path_template(url: httpx.URL) -> str:
    """
    The path with every identifying segment as `*` (no query, no fragment);
    API versions stay.
    """

    return "/".join(map(template_segment, url.path.split("/"))) or "/"


def template_segment(segment: str) -> str:
    if VERSION_SEGMENT.match(segment):
        return segment

    if IDENTIFYING_SEGMENT.search(segment) or len(segment) > LONGEST_KEPT_SEGMENT:
        return MASKED_SEGMENT

    return segment


def call_span_name(request: httpx.Request) -> str:
    return f"{request.method} {request.url.host}"


def install_http_client_spans(tracer: SpanTracer) -> bool:
    """
    Give every httpx call of this process a client span; True when it was
    installed now (once per process; a tracer that records nothing installs
    nothing).
    """

    if not tracer.is_recording:
        return False

    with _install_lock:
        real_send: Send = httpx.Client.send
        if getattr(real_send, WRAPPED_MARK, False):
            return False

        def send(
            self: httpx.Client, request: httpx.Request, **kwargs: object
        ) -> httpx.Response:
            with tracer.span(
                call_span_name(request),
                SpanKind.CLIENT,
                {
                    "http.request.method": request.method,
                    "server.address": request.url.host,
                    "url.scheme": request.url.scheme,
                    "url.template": path_template(request.url),
                },
            ) as span:
                response: httpx.Response = real_send(self, request, **kwargs)
                span.set_attribute("http.response.status_code", response.status_code)
                if response.status_code >= SERVER_ERROR_STATUS:
                    span.mark_failed(f"HTTP {response.status_code}")
                return response

        setattr(send, WRAPPED_MARK, True)
        httpx.Client.send = send  # type: ignore[method-assign]
        return True
