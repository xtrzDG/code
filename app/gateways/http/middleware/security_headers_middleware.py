"""Security headers of every API answer (a standard header review)."""

from collections.abc import Awaitable, Callable

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

type ErrorHandler = Callable[[Request, Exception], Awaitable[Response]]

STRICT_TRANSPORT_SECURITY: str = "max-age=63072000; includeSubDomains"
# The API answers JSON, audio and two static files: nothing may frame it,
# and a JSON answer opened as a page runs nothing.
API_CONTENT_SECURITY_POLICY: str = "default-src 'none'; frame-ancestors 'none'"
# The interactive API description (outside production only) loads its
# script and styles from a CDN, so it keeps no policy of its own.
API_DESCRIPTION_PATHS: frozenset[str] = frozenset(
    {"/docs", "/docs/oauth2-redirect", "/redoc"}
)
API_PATH_PREFIX: str = "/v1/"


class SecurityHeadersMiddleware:
    """
    Adds what a header review expects to every answer that does not set it
    itself: `X-Content-Type-Options: nosniff`, `Referrer-Policy:
    no-referrer`, `X-Frame-Options: DENY` with a `frame-ancestors 'none'`
    policy, `Cache-Control: no-store` on the API routes (their answers are
    personal or change at once; routes that may be cached say so, like the
    widget script), and in production `Strict-Transport-Security` (two
    years, subdomains included).
    """

    def __init__(self, app: ASGIApp, is_https_only: bool) -> None:
        self.app: ASGIApp = app
        self._is_https_only: bool = is_https_only

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = str(scope.get("path", ""))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                add_security_headers(
                    MutableHeaders(scope=message), path, self._is_https_only
                )

            await send(message)

        await self.app(scope, receive, send_with_headers)


def add_security_headers(
    headers: MutableHeaders,
    path: str,
    is_https_only: bool,
) -> None:
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("Referrer-Policy", "no-referrer")
    if path not in API_DESCRIPTION_PATHS:
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Content-Security-Policy", API_CONTENT_SECURITY_POLICY)

    if path.startswith(API_PATH_PREFIX):
        headers.setdefault("Cache-Control", "no-store")

    if is_https_only:
        headers.setdefault("Strict-Transport-Security", STRICT_TRANSPORT_SECURITY)


def with_security_headers(handler: ErrorHandler, is_https_only: bool) -> ErrorHandler:
    """
    The handler of unexpected errors, whose 500 answer leaves the stack
    outside every middleware, with the security headers added.
    """

    async def handle(request: Request, error: Exception) -> Response:
        response: Response = await handler(request, error)
        add_security_headers(response.headers, request.url.path, is_https_only)
        return response

    return handle
