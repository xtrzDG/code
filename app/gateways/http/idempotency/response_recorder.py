"""
The answers of creating requests that hold an idempotency key: kept when
they succeed, the key released when they do not, before the client sees
them.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.gateways.http.idempotency.idempotent_requests import (
    IDEMPOTENT_REPLAY_HEADER,
    SLOT_SCOPE_KEY,
    IdempotencySlot,
    IdempotentReplay,
    PendingIdempotentRequest,
)
from app.schemas.dto.idempotency import StoredResponse
from app.schemas.typings.idempotency.constrained_integers import StoredResponseStatus
from app.schemas.typings.idempotency.constrained_strings import (
    StoredResponseMediaType,
)
from app.schemas.typings.idempotency.strings import StoredResponseBody

logger: logging.Logger = logging.getLogger(__name__)

WRITING_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULT_MEDIA_TYPE: str = "application/json"
# Creating requests answer a few KB; a bigger answer is passed on, not kept.
MAX_STORED_RESPONSE_BYTES: int = 256 * 1024


def install_idempotency(http_application: FastAPI) -> None:
    """The recorder around the routes and the answer for a replayed request."""

    http_application.add_middleware(IdempotentResponseRecorder)
    http_application.add_exception_handler(IdempotentReplay, replay_stored_response)


async def replay_stored_response(request: Request, error: Exception) -> Response:
    del request
    if not isinstance(error, IdempotentReplay):  # pragma: no cover - registration
        raise error

    stored: StoredResponse = error.response
    return Response(
        content=str(stored.body).encode(),
        status_code=int(stored.status),
        media_type=str(stored.media_type),
        headers={IDEMPOTENT_REPLAY_HEADER: "true"},
    )


class IdempotentResponseRecorder:
    """
    Pure ASGI middleware. For a writing request it leaves an empty slot in
    the scope; when the idempotency dependency claimed a key into it, the
    answer is held back until its last byte, then kept (2xx) or the key
    released (any other status), and only then sent, so a retry that
    arrives after the answer finds the key settled. An unhandled error
    releases the key too (the 500 is the server error middleware's). A
    failure to settle the key is logged and the answer still goes out: the
    claim's lease frees the key later.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in WRITING_METHODS:
            await self.app(scope, receive, send)
            return

        slot = IdempotencySlot()
        scope[SLOT_SCOPE_KEY] = slot
        recording = ResponseRecording(slot, send)
        try:
            await self.app(scope, receive, recording.send)
        except Exception:
            # A cancelled request (the client left) keeps its key held: its
            # work may still finish, and the lease frees the key later.
            await recording.settle_unanswered()
            raise


class ResponseRecording:
    """The answer of one request, held back while its key is settled."""

    def __init__(self, slot: IdempotencySlot, send: Send) -> None:
        self._slot: IdempotencySlot = slot
        self._send: Send = send
        self._start: Message | None = None
        self._body: bytearray = bytearray()
        self._is_passing_through: bool = False

    async def send(self, message: Message) -> None:
        pending: PendingIdempotentRequest | None = self._slot.pending
        if pending is None or self._is_passing_through:
            await self._send(message)
            return

        if message["type"] == "http.response.start":
            self._start = message
            return

        if message["type"] != "http.response.body" or self._start is None:
            await self._send(message)
            return

        self._body.extend(message.get("body", b""))
        if len(self._body) > MAX_STORED_RESPONSE_BYTES:
            await self._settle(pending, None)
            await self._flush(more_body=bool(message.get("more_body", False)))
            self._is_passing_through = True
            return

        if message.get("more_body", False):
            return

        await self._settle(pending, stored_response(self._start, bytes(self._body)))
        await self._flush(more_body=False)

    async def settle_unanswered(self) -> None:
        """Release a key whose request failed before its answer was settled."""

        pending: PendingIdempotentRequest | None = self._slot.pending
        if pending is not None:
            await self._settle(pending, None)

    async def _settle(
        self, pending: PendingIdempotentRequest, response: StoredResponse | None
    ) -> None:
        self._slot.pending = None
        try:
            await run_in_threadpool(pending.finish, pending.outcome(response))
        except Exception:  # noqa: BLE001 - the answer must still go out
            logger.exception(
                "Could not settle idempotency key %s; its lease frees it.",
                pending.record_id,
            )

    async def _flush(self, more_body: bool) -> None:
        if self._start is not None:
            await self._send(self._start)
        await self._send(
            {
                "type": "http.response.body",
                "body": bytes(self._body),
                "more_body": more_body,
            }
        )
        self._body.clear()


def stored_response(start: Message, body: bytes) -> StoredResponse | None:
    """The answer to keep: a 2xx with a UTF-8 body; None releases the key."""

    status: int = int(start.get("status", 500))
    if not 200 <= status <= 299:
        return None

    try:
        text: str = body.decode("utf-8")
    except UnicodeDecodeError:
        return None

    return StoredResponse(
        status=StoredResponseStatus(status),
        media_type=StoredResponseMediaType(media_type_of(start)),
        body=StoredResponseBody(text),
    )


def media_type_of(start: Message) -> str:
    for name, value in start.get("headers", []):
        if bytes(name).lower() == b"content-type":
            return bytes(value).decode("latin-1")

    return DEFAULT_MEDIA_TYPE
