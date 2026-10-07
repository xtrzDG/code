"""
The generic per-address limit of requests without a token
(API_REQUESTS_PER_IP_PER_MINUTE): a 429 with Retry-After before any route
runs. Signed-in requests count per person in the bearer dependency
instead (`request_limits`). Routes with limits of their own or callers
that are not browsers are left alone: the website chat (per visitor,
network, business and platform), the providers' webhooks (Telegram, Meta,
ElevenLabs, Zadarma, Flitt send from few addresses in bursts), the
landing page's demos, the widget script, health checks and the API
description.
"""

from collections.abc import Callable

from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Receive, Scope, Send

from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.errors import ErrorBody
from app.schemas.dto.spend_guard import ApiRequestAdmission
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.strings import ErrorMessageText

type AdmitRequest = Callable[[ApiRequestAdmission], None]

EXEMPT_PREFIXES: tuple[str, ...] = (
    "/healthz",
    "/readyz",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/widget",
    "/v1/widget/",
    "/v1/channels/",
    "/v1/voice/",
    "/v1/telephony/",
    "/v1/payments/",
    "/v1/public-demos",
)


def is_exempt(scope: Scope) -> bool:
    """Routes with limits of their own, preflights and signed-in requests."""

    path: str = str(scope.get("path", ""))
    if scope.get("method") == "OPTIONS" or path.startswith(EXEMPT_PREFIXES):
        return True

    headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []))
    return any(name.lower() == b"authorization" for name, _ in headers)


class AnonymousRequestLimitMiddleware:
    """Counts each request without a token against its client network."""

    def __init__(self, app: ASGIApp, admit: AdmitRequest) -> None:
        self.app: ASGIApp = app
        self._admit: AdmitRequest = admit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        client: tuple[str, int] | None = scope.get("client")
        if scope["type"] != "http" or client is None or is_exempt(scope):
            await self.app(scope, receive, send)
            return

        admission = ApiRequestAdmission(client_ip_address=ClientIpAddress(client[0]))
        try:
            await run_in_threadpool(self._admit, admission)
        except RateLimitedError as error:
            await send_too_many_requests(send, error)
            return

        await self.app(scope, receive, send)


async def send_too_many_requests(send: Send, error: RateLimitedError) -> None:
    body: bytes = (
        ErrorBody(
            error=ApiErrorCode.RATE_LIMITED,
            message=ErrorMessageText(str(error)),
        )
        .model_dump_json(exclude_none=True)
        .encode("utf-8")
    )
    headers: list[tuple[bytes, bytes]] = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("latin-1")),
    ]
    if error.retry_after_seconds is not None:
        headers.append(
            (b"retry-after", str(int(error.retry_after_seconds)).encode("latin-1"))
        )

    await send({"type": "http.response.start", "status": 429, "headers": headers})
    await send({"type": "http.response.body", "body": body})
