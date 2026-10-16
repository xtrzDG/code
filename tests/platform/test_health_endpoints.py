"""
/healthz is liveness without threads; /readyz tells the truth about the
database, fast, also when every request thread is busy.
"""

import asyncio
import threading
import time
from collections.abc import Mapping

import anyio.to_thread
import httpx
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.containers.app import AppContainer
from app.gateways.http import health_routes
from app.gateways.http.application import build_http_application
from app.gateways.http.health_routes import build_readiness_router
from app.main import build_application
from app.schemas.dto.health import ReadinessQuery, ReadinessReport
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider
from tests.platform.test_http_application import RecordingErrorReporter

# Nothing listens on port 1: the connection is refused at once.
UNREACHABLE_DATABASE_URL: str = "postgresql://workshop@127.0.0.1:1/workshop"
SLOW_REQUESTS: int = 64


def build_client(environment: Mapping[str, str]) -> TestClient:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    return TestClient(build_application(container))


def test_without_a_database_the_instance_is_ready_and_says_why() -> None:
    response = build_client({}).get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == {"status": "skipped"}
    assert body["checks"]["worker"]["status"] == "degraded"


def test_readyz_fails_while_the_database_is_down() -> None:
    client = build_client({"DATABASE_URL": UNREACHABLE_DATABASE_URL})

    readiness = client.get("/readyz")
    liveness = client.get("/healthz")

    assert readiness.status_code == 503
    body = readiness.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == {"status": "failed", "failure": "unreachable"}
    assert body["checks"]["migrations"] == {"status": "failed"}
    assert body["checks"]["worker"] == {"status": "degraded"}
    # Liveness never touches the database: the process itself is fine.
    assert liveness.status_code == 200


class SlowReadiness:
    """A check that hangs until the test releases it (or gives up on it)."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.returned = threading.Event()

    def operate(self, input_data: ReadinessQuery) -> ReadinessReport:
        del input_data
        self.release.wait(timeout=5)
        self.returned.set()
        raise AssertionError("The readiness deadline should have passed first.")


def test_a_readiness_check_that_hangs_answers_not_ready_in_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_routes, "READINESS_DEADLINE_SECONDS", 0.2)
    slow = SlowReadiness()
    client = TestClient(
        build_http_application(
            routers=[build_readiness_router(slow)],
            error_reporter=RecordingErrorReporter(),
            cors_allowed_origins=[],
        )
    )

    response = client.get("/readyz")
    # The answer came while the check still hung: the deadline, not the check.
    answered_first: bool = not slow.returned.is_set()
    slow.release.set()

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == {
        "status": "failed",
        "failure": "timeout",
    }
    assert answered_first


def test_healthz_answers_while_slow_requests_hold_every_request_thread() -> None:
    release = threading.Event()
    entered = threading.Semaphore(0)
    router = APIRouter()

    @router.get("/slow")
    def slow() -> dict[str, str]:
        entered.release()
        release.wait(timeout=10)
        return {"status": "done"}

    application = build_http_application(
        routers=[router],
        error_reporter=RecordingErrorReporter(),
        cors_allowed_origins=[],
    )

    async def scenario() -> tuple[int, float, int, list[int]]:
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = SLOW_REQUESTS
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://api"
        ) as client:
            slow_requests = [
                asyncio.create_task(client.get("/slow")) for _ in range(SLOW_REQUESTS)
            ]
            for _ in range(SLOW_REQUESTS):
                await asyncio.to_thread(entered.acquire, True, 5)
            busy_threads: int = int(limiter.borrowed_tokens)

            started = time.monotonic()
            health = await asyncio.wait_for(client.get("/healthz"), timeout=2)
            elapsed = time.monotonic() - started

            release.set()
            finished = await asyncio.gather(*slow_requests)
            return (
                health.status_code,
                elapsed,
                busy_threads,
                [response.status_code for response in finished],
            )

    try:
        status, elapsed, busy_threads, slow_statuses = asyncio.run(scenario())
    finally:
        release.set()

    assert busy_threads == SLOW_REQUESTS
    assert status == 200
    assert elapsed < 1
    assert slow_statuses == [200] * SLOW_REQUESTS
