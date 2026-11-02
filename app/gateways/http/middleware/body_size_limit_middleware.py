"""
Request body limits of the API: a body over its route's limit is refused
with 413 before (or while) it is read, so no route ever holds more.
"""

import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.gateways.http.middleware.error_answers import client_address_of
from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.errors import ErrorBody
from app.schemas.typings.platform.strings import ErrorMessageText
from app.utilities.channels.channel_endpoints import (
    META_WEBHOOK_PATH,
    TELEGRAM_PLATFORM_WEBHOOK_PATH,
    VOICE_CALL_INITIATION_PATH,
    VOICE_POST_CALL_PATH,
)
from app.utilities.observability.security_events import (
    REQUEST_BODY_REFUSED,
    log_security_event,
)

KIBIBYTE: int = 1024
MEBIBYTE: int = 1024 * KIBIBYTE
# JSON of a cabinet form, a widget message or a sign-in.
DEFAULT_BODY_LIMIT_BYTES: int = 256 * KIBIBYTE
# A request that only reads (GET, HEAD, OPTIONS) has no use for a body.
READING_BODY_LIMIT_BYTES: int = KIBIBYTE
READING_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})
# A telephony line's call notification: a form of a few dozen short fields.
TELEPHONY_FORM_BODY_LIMIT_BYTES: int = 64 * KIBIBYTE
# Batched platform deliveries (Meta, Telegram, Flitt, a call's start).
WEBHOOK_BODY_LIMIT_BYTES: int = MEBIBYTE
# The full transcript and analysis of a long call (ElevenLabs).
POST_CALL_BODY_LIMIT_BYTES: int = 5 * MEBIBYTE
# A 15 MB menu photo or PDF as base64 (4 characters per 3 bytes) in JSON.
MENU_IMPORT_BODY_LIMIT_BYTES: int = 21 * MEBIBYTE
# A website visitor's photo or voice note: the largest cap a file kind may
# have (MEDIA_MAX_*_BYTES, at most 25 MiB) and its form; the route itself
# stops reading at the cap configured for the business's files.
WIDGET_UPLOAD_BODY_LIMIT_BYTES: int = 26 * MEBIBYTE
BODY_LIMITS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"^/v1/widget/[^/]+/attachments$"), WIDGET_UPLOAD_BODY_LIMIT_BYTES),
    (
        re.compile(r"^/v1/businesses/[^/]+/knowledge/import$"),
        MENU_IMPORT_BODY_LIMIT_BYTES,
    ),
    (re.compile(rf"^{re.escape(VOICE_POST_CALL_PATH)}$"), POST_CALL_BODY_LIMIT_BYTES),
    (re.compile(r"^/v1/telephony/"), TELEPHONY_FORM_BODY_LIMIT_BYTES),
    (
        re.compile(
            r"^(/v1/channels/telegram/[^/]+/webhook"
            rf"|{re.escape(TELEGRAM_PLATFORM_WEBHOOK_PATH)}"
            rf"|{re.escape(META_WEBHOOK_PATH)}"
            rf"|{re.escape(VOICE_CALL_INITIATION_PATH)}"
            r"|/v1/payments/[^/]+/webhook)$"
        ),
        WEBHOOK_BODY_LIMIT_BYTES,
    ),
)


class RequestBodyTooLargeError(Exception):
    """The body grew over its limit while a route was reading it."""


class BodySizeLimitMiddleware:
    """
    Refuses a request body over the limit of its route with 413
    `payload_too_large`: 1 KB for a request that only reads, 256 KB by
    default, 64 KB for a telephony line's notification, 1 MB for platform
    webhooks, 5 MB for the post-call report, 21 MB for a menu import (a
    15 MB file in base64) and 26 MB for a website visitor's upload. A declared
    Content-Length over the limit is refused before any byte is read; a
    chunked or understated body is counted as it streams, and reading
    stops at the limit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit: int = find_body_limit(
            str(scope.get("path", "")), str(scope.get("method", ""))
        )
        declared_length: int | None = read_content_length(scope)
        if declared_length is not None and declared_length > limit:
            refuse_body(scope, "declared_too_large")
            await send_payload_too_large(send, limit)
            return

        received: int = 0
        is_response_started: bool = False

        async def counting_receive() -> Message:
            nonlocal received
            message: Message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise RequestBodyTooLargeError()

            return message

        async def tracking_send(message: Message) -> None:
            nonlocal is_response_started
            if message["type"] == "http.response.start":
                is_response_started = True

            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except RequestBodyTooLargeError:
            if is_response_started:
                raise

            refuse_body(scope, "streamed_too_large")
            await send_payload_too_large(send, limit)


def find_body_limit(path: str, method: str = "POST") -> int:
    if method.upper() in READING_METHODS:
        return READING_BODY_LIMIT_BYTES

    for pattern, limit in BODY_LIMITS:
        if pattern.match(path):
            return limit

    return DEFAULT_BODY_LIMIT_BYTES


def read_content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            raw_value: str = value.decode("latin-1").strip()
            return int(raw_value) if raw_value.isdigit() else None

    return None


def refuse_body(scope: Scope, reason: str) -> None:
    log_security_event(
        REQUEST_BODY_REFUSED,
        path=route_class_of(str(scope.get("path", ""))),
        reason=reason,
        client_address=client_address_of(scope),
    )


def route_class_of(path: str) -> str:
    """The pattern of the limit a path falls under (logs carry no ids)."""

    for pattern, _ in BODY_LIMITS:
        if pattern.match(path):
            return pattern.pattern

    return "default"


async def send_payload_too_large(send: Send, limit: int) -> None:
    body: bytes = (
        ErrorBody(
            error=ApiErrorCode.PAYLOAD_TOO_LARGE,
            message=ErrorMessageText(
                f"The request body is larger than the {limit // KIBIBYTE} KB "
                "allowed here."
            ),
        )
        .model_dump_json(exclude_none=True)
        .encode("utf-8")
    )
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
