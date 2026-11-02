"""
The deadline of an API request: a route that has not started its answer
within its deadline is answered 504 at once (the `ErrorBody` code every
504 of the API has, `error_code_for_status`).

The deadline runs only until the answer starts, so streams (the live
events, CSV exports, recordings) are never cut: they start answering at
once and then take as long as they need. A WebSocket is not an HTTP
request and is left alone. The route itself is not interrupted (a route's
thread cannot be): it finishes on its own, its answer is dropped, and a
creating request with an Idempotency-Key keeps that answer for the retry.
"""

import asyncio
import logging
import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.gateways.http.error_responses import error_code_for_status
from app.gateways.http.middleware.error_answers import (
    client_address_of,
    send_error_answer,
)
from app.utilities.observability.security_events import (
    REQUEST_DEADLINE_EXCEEDED,
    log_security_event,
)

LOGGER: logging.Logger = logging.getLogger(__name__)

API_PATH_PREFIX: str = "/v1/"
GATEWAY_TIMEOUT: int = 504
# A cabinet form, a list, a widget message (the assistant answers later).
DEFAULT_DEADLINE_SECONDS: float = 60.0
# Routes that wait for the model (assembling an assistant, autotests, the
# test chat, imports, suggestions) or for a large upload: just under the
# cabinet proxy's own 180 s, so its caller gets this answer, not a cut.
LONG_DEADLINE_SECONDS: float = 170.0
LONG_DEADLINE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"^/v1/assistants$",
        r"^/v1/businesses/[^/]+/assistant(/|-versions|$)",
        r"^/v1/businesses/[^/]+/autotest-cases",
        r"^/v1/businesses/[^/]+/test-chat",
        r"^/v1/businesses/[^/]+/knowledge/",
        r"^/v1/businesses/[^/]+/setup",
        r"^/v1/businesses/[^/]+/conversations/[^/]+/messages/[^/]+/correction$",
        r"^/v1/widget/[^/]+/attachments$",
    )
)
TIMEOUT_MESSAGE: str = "The request took too long and was stopped; try again."
# Routes still running after their answer was given up on: kept referenced
# until they finish, so the event loop does not drop them.
_ABANDONED: set[asyncio.Task[None]] = set()


def deadline_of(path: str) -> float:
    if any(pattern.match(path) for pattern in LONG_DEADLINE_PATTERNS):
        return LONG_DEADLINE_SECONDS

    return DEFAULT_DEADLINE_SECONDS


class RequestDeadlineMiddleware:
    """Pure ASGI middleware around the API routes (paths under /v1/)."""

    def __init__(
        self,
        app: ASGIApp,
        default_seconds: float = DEFAULT_DEADLINE_SECONDS,
        long_seconds: float = LONG_DEADLINE_SECONDS,
    ) -> None:
        self.app: ASGIApp = app
        self._default_seconds: float = default_seconds
        self._long_seconds: float = long_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path: str = str(scope.get("path", ""))
        if scope["type"] != "http" or not path.startswith(API_PATH_PREFIX):
            await self.app(scope, receive, send)
            return

        started: asyncio.Event = asyncio.Event()
        given_up: list[bool] = [False]

        async def guarded_send(message: Message) -> None:
            if given_up[0]:
                return
            if message["type"] == "http.response.start":
                started.set()
            await send(message)

        route: asyncio.Task[None] = asyncio.ensure_future(
            self.app(scope, receive, guarded_send)
        )
        waiting_for_start: asyncio.Task[bool] = asyncio.ensure_future(started.wait())
        deadline: float = (
            self._long_seconds
            if deadline_of(path) == LONG_DEADLINE_SECONDS
            else self._default_seconds
        )
        try:
            await asyncio.wait(
                {route, waiting_for_start},
                timeout=deadline,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            waiting_for_start.cancel()

        if route.done() or started.is_set():
            # Finished, or answering (a stream): no deadline from here on.
            await route
            return

        given_up[0] = True
        _ABANDONED.add(route)
        route.add_done_callback(forget_abandoned)
        log_security_event(
            REQUEST_DEADLINE_EXCEEDED,
            path=str(scope.get("method", "")) + " " + route_template_of(path),
            reason=f"no_answer_within_{int(deadline)}s",
            client_address=client_address_of(scope),
        )
        await send_error_answer(
            send,
            GATEWAY_TIMEOUT,
            error_code_for_status(GATEWAY_TIMEOUT),
            TIMEOUT_MESSAGE,
        )


def forget_abandoned(route: asyncio.Task[None]) -> None:
    """Drop a route whose answer was given up on, logging how it ended."""

    _ABANDONED.discard(route)
    if route.cancelled():
        return

    error: BaseException | None = route.exception()
    if error is not None:
        LOGGER.warning(
            "A request answered 504 ended with %s after its deadline",
            type(error).__name__,
        )


def route_template_of(path: str) -> str:
    """The first two segments of the path (no ids in a security log)."""

    return "/" + "/".join(path.split("/")[1:3])
