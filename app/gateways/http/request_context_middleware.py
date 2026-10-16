"""
The request id of every HTTP request: taken from X-Request-ID when the
caller sent a usable one, otherwise generated; bound to the log context for
the whole request (also inside the request threads) and echoed in the
response.
"""

import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.schemas.typings.platform.constrained_strings import RequestId
from app.utilities.observability.log_context import bound_log_context

REQUEST_ID_HEADER: str = "X-Request-ID"
MAX_REQUEST_ID_LENGTH: int = 128


class RequestContextMiddleware:
    """
    Pure ASGI middleware (no extra task per request, unlike
    BaseHTTPMiddleware), so the bound context reaches every handler and the
    error it may raise carries it.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id: RequestId = sanitize_request_id(
            Headers(scope=scope).get(REQUEST_ID_HEADER)
        )

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = str(request_id)
            await send(message)

        with bound_log_context(request_id=request_id):
            await self._app(scope, receive, send_with_request_id)


def sanitize_request_id(raw_request_id: str | None) -> RequestId:
    """Keep a caller's request id if it is short and printable, else make one."""

    if (
        raw_request_id is not None
        and 0 < len(raw_request_id) <= MAX_REQUEST_ID_LENGTH
        and raw_request_id.isascii()
        and raw_request_id.isprintable()
    ):
        return RequestId(raw_request_id)

    return RequestId(str(uuid.uuid4()))
