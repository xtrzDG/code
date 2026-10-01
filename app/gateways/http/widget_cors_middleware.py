"""CORS headers on every response of the public website-widget routes."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

WIDGET_PATH_PREFIX: str = "/v1/widget/"
# The website widget runs on every business's own site, so its public routes
# allow any origin. It may post with Content-Type text/plain (the body is
# still JSON) to avoid a CORS preflight when an application restricts
# origins globally.
WIDGET_CORS_HEADERS: dict[str, str] = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
}


def is_widget_path(path: str) -> bool:
    return path.startswith(WIDGET_PATH_PREFIX)


class WidgetCorsMiddleware:
    """
    Every response of the public widget routes carries the widget CORS
    headers, errors included (a 404 for a disabled chat, a 422 for a bad
    body, a 429), so the widget on a business's site can read the status
    instead of seeing an opaque network error.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not is_widget_path(str(scope.get("path", ""))):
            await self.app(scope, receive, send)
            return

        async def send_with_cors(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw_headers: list[tuple[bytes, bytes]] = list(
                    message.get("headers", [])
                )
                present: set[bytes] = {name.lower() for name, _ in raw_headers}
                for name, value in WIDGET_CORS_HEADERS.items():
                    if name.lower().encode("latin-1") not in present:
                        raw_headers.append(
                            (name.lower().encode("latin-1"), value.encode("latin-1"))
                        )

                message = {**message, "headers": raw_headers}

            await send(message)

        await self.app(scope, receive, send_with_cors)
