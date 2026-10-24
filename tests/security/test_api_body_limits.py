"""Request body limits of the API: 413 before or while a body is read."""

import asyncio
from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, Request
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from app.gateways.http.application import build_http_application
from app.gateways.http.middleware.body_size_limit_middleware import (
    DEFAULT_BODY_LIMIT_BYTES,
    MENU_IMPORT_BODY_LIMIT_BYTES,
    POST_CALL_BODY_LIMIT_BYTES,
    WEBHOOK_BODY_LIMIT_BYTES,
    BodySizeLimitMiddleware,
    find_body_limit,
)
from app.gateways.http.middleware.security_headers_middleware import (
    SecurityHeadersMiddleware,
)
from app.gateways.http.strict_request_parsing import read_raw_request_body
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl

KIBIBYTE: int = 1024


class SilentErrorReporter:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def capture_exception(self, error: BaseException) -> None:
        self.errors.append(error)


def build_client() -> tuple[TestClient, SilentErrorReporter]:
    router = APIRouter()

    @router.post("/v1/echo")
    def echo(body: Annotated[bytes, Depends(read_raw_request_body)]) -> dict[str, int]:
        return {"length": len(body)}

    @router.post("/v1/channels/meta/webhook")
    async def webhook(request: Request) -> dict[str, int]:
        return {"length": len(await request.body())}

    reporter = SilentErrorReporter()
    application = build_http_application(
        routers=[router],
        error_reporter=reporter,
        cors_allowed_origins=[PublicBaseUrl("https://cabinet.example.com")],
    )
    return TestClient(application, raise_server_exceptions=False), reporter


def chunks(total: int, size: int = 64 * KIBIBYTE) -> Iterator[bytes]:
    """A body without Content-Length (chunked), `total` bytes long."""

    while total > 0:
        yield b"x" * min(size, total)
        total -= size


@pytest.mark.parametrize(
    ("path", "limit"),
    [
        ("/v1/me", DEFAULT_BODY_LIMIT_BYTES),
        ("/v1/auth/otp/start", DEFAULT_BODY_LIMIT_BYTES),
        ("/v1/widget/biz_1/messages", DEFAULT_BODY_LIMIT_BYTES),
        ("/v1/channels/telegram/channel_1/webhook", WEBHOOK_BODY_LIMIT_BYTES),
        ("/v1/channels/telegram-platform/webhook", WEBHOOK_BODY_LIMIT_BYTES),
        ("/v1/channels/meta/webhook", WEBHOOK_BODY_LIMIT_BYTES),
        ("/v1/payments/flitt/webhook", WEBHOOK_BODY_LIMIT_BYTES),
        ("/v1/voice/webhooks/conversation-initiation", WEBHOOK_BODY_LIMIT_BYTES),
        ("/v1/voice/webhooks/post-call", POST_CALL_BODY_LIMIT_BYTES),
        ("/v1/businesses/biz_1/knowledge/import", MENU_IMPORT_BODY_LIMIT_BYTES),
        ("/v1/businesses/biz_1/knowledge/import/confirm", DEFAULT_BODY_LIMIT_BYTES),
    ],
)
def test_every_route_has_its_body_limit(path: str, limit: int) -> None:
    assert find_body_limit(path) == limit


def test_a_body_within_the_limit_is_read() -> None:
    client, _ = build_client()

    response = client.post("/v1/echo", content=b"x" * DEFAULT_BODY_LIMIT_BYTES)

    assert response.status_code == 200
    assert response.json() == {"length": DEFAULT_BODY_LIMIT_BYTES}


def test_a_declared_length_over_the_limit_is_refused_before_reading() -> None:
    client, reporter = build_client()

    response = client.post("/v1/echo", content=b"x" * (DEFAULT_BODY_LIMIT_BYTES + 1))

    assert response.status_code == 413
    assert response.json() == {
        "error": "payload_too_large",
        "message": "The request body is larger than the 256 KB allowed here.",
    }
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert reporter.errors == []


def test_a_streamed_body_is_counted_and_stopped_at_the_limit() -> None:
    client, reporter = build_client()

    refused = client.post("/v1/echo", content=chunks(DEFAULT_BODY_LIMIT_BYTES * 2))
    webhook = client.post(
        "/v1/channels/meta/webhook", content=chunks(DEFAULT_BODY_LIMIT_BYTES * 2)
    )

    assert refused.status_code == 413
    assert refused.json()["error"] == "payload_too_large"
    assert webhook.status_code == 200
    assert webhook.json() == {"length": DEFAULT_BODY_LIMIT_BYTES * 2}
    assert reporter.errors == []


def test_a_refused_cabinet_body_still_answers_with_cors() -> None:
    client, _ = build_client()

    response = client.post(
        "/v1/echo",
        content=b"x" * (DEFAULT_BODY_LIMIT_BYTES + 1),
        headers={"Origin": "https://cabinet.example.com"},
    )

    assert response.status_code == 413
    assert (
        response.headers["Access-Control-Allow-Origin"] == "https://cabinet.example.com"
    )


def test_other_connections_pass_through_both_middlewares() -> None:
    seen: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del receive, send
        seen.append(str(scope["type"]))

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        del message

    asyncio.run(BodySizeLimitMiddleware(app)({"type": "lifespan"}, receive, send))
    asyncio.run(
        SecurityHeadersMiddleware(app, is_https_only=True)(
            {"type": "websocket", "path": "/ws"}, receive, send
        )
    )

    assert seen == ["lifespan", "websocket"]
