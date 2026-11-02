"""
An API route that has not started its answer within its deadline is
answered 504; a stream that started in time runs as long as it needs, and
paths outside /v1/ have no deadline.
"""

import asyncio
import re
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app.gateways.http.middleware.request_deadline_middleware import (
    DEFAULT_DEADLINE_SECONDS,
    LONG_DEADLINE_PATTERNS,
    LONG_DEADLINE_SECONDS,
    RequestDeadlineMiddleware,
    deadline_of,
)
from tests.e2e.harness import start_workshop

SHORT: float = 0.2


def build_client() -> TestClient:
    application = FastAPI()

    @application.get("/v1/slow")
    async def slow() -> dict[str, str]:
        await asyncio.sleep(SHORT * 5)
        return {"late": "yes"}

    @application.get("/v1/quick")
    async def quick() -> dict[str, str]:
        return {"quick": "yes"}

    @application.get("/v1/stream")
    async def stream() -> StreamingResponse:
        async def chunks() -> AsyncIterator[bytes]:
            for _ in range(3):
                await asyncio.sleep(SHORT)
                yield b"chunk\n"

        return StreamingResponse(chunks(), media_type="text/plain")

    @application.get("/slow-probe")
    async def probe() -> dict[str, str]:
        await asyncio.sleep(SHORT * 2)
        return {"probe": "ok"}

    @application.get("/v1/boom")
    async def boom() -> None:
        raise RuntimeError("fails before its deadline")

    return TestClient(
        RequestDeadlineMiddleware(
            application, default_seconds=SHORT, long_seconds=SHORT
        ),
        raise_server_exceptions=True,
    )


def test_a_route_past_its_deadline_is_answered_504() -> None:
    response = build_client().get("/v1/slow")

    assert response.status_code == 504
    assert response.json() == {
        "error": "external_service_error",
        "message": "The request took too long and was stopped; try again.",
    }


def test_routes_in_time_streams_and_probes_are_not_cut() -> None:
    client = build_client()

    assert client.get("/v1/quick").json() == {"quick": "yes"}
    streamed = client.get("/v1/stream")
    assert streamed.status_code == 200
    assert streamed.text == "chunk\n" * 3
    assert client.get("/slow-probe").json() == {"probe": "ok"}


def test_an_error_before_the_deadline_still_reaches_the_error_handling() -> None:
    with pytest.raises(RuntimeError, match="fails before its deadline"):
        build_client().get("/v1/boom")


def test_model_routes_and_uploads_have_the_long_deadline() -> None:
    assert deadline_of("/v1/businesses/b/test-chat") == LONG_DEADLINE_SECONDS
    assert deadline_of("/v1/businesses/b/knowledge/import") == LONG_DEADLINE_SECONDS
    assert deadline_of("/v1/widget/b/attachments") == LONG_DEADLINE_SECONDS
    assert deadline_of("/v1/businesses/b/bookings") == DEFAULT_DEADLINE_SECONDS
    assert deadline_of("/v1/widget/b/messages") == DEFAULT_DEADLINE_SECONDS
    # Under the cabinet proxy's own 180 s, so its caller gets the 504.
    assert DEFAULT_DEADLINE_SECONDS < LONG_DEADLINE_SECONDS < 180


def test_every_long_deadline_pattern_names_routes_that_exist() -> None:
    templates: list[str] = list(start_workshop().application.openapi()["paths"])
    for pattern in LONG_DEADLINE_PATTERNS:
        concrete: list[str] = [
            re.sub(r"\{[a-z_]+\}", "x", template) for template in templates
        ]
        assert any(pattern.match(path) for path in concrete), pattern.pattern
