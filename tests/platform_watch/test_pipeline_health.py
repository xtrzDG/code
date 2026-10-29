"""
GET /healthz/pipeline: 200 while a worker pulsed within five minutes and no
customer message waited over 120 s; 503 on either, when the database
cannot tell, or when it cannot tell in time. No token, not in the API
description, never cached.
"""

import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.gateways.http import pipeline_health_routes
from app.gateways.http.pipeline_health_routes import build_pipeline_health_router
from app.main import build_application
from app.repositories.worker_heartbeat_repository import WorkerHeartbeatRepository
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.observability import HealthCheckStatus, PipelineState
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.pipeline_health import PipelineHealthQuery, PipelineHealthReport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.use_cases.observability.check_pipeline_health_use_case import (
    CheckPipelineHealthUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.monitoring.pipeline_health import assess_pipeline, seconds_since
from tests.e2e.workshop_container import replace_provider
from tests.platform_ops.ops_documents import NOW, SECOND, at, job, pulse
from tests.platform_watch.watch_world import WatchWorld


def health(world: WatchWorld) -> PipelineHealthReport:
    return CheckPipelineHealthUseCase(
        world.heartbeat_repo, world.health_repo, world.clock.wall_clock
    ).run(PipelineHealthQuery())


def test_a_fresh_pulse_and_no_waiting_customer_is_flowing() -> None:
    world = WatchWorld()
    world.worker_beats()
    world.customer_waits_since(30)

    report = health(world)

    assert report.status is PipelineState.FLOWING
    assert int(report.checks.inbound.waiting) == 1
    assert report.checks.inbound.oldest_wait_seconds == 30


@pytest.mark.parametrize(
    ("pulse_age_seconds", "expected"),
    [(300, PipelineState.FLOWING), (301, PipelineState.STALLED)],
)
def test_the_worker_check_allows_five_minutes(
    pulse_age_seconds: int, expected: PipelineState
) -> None:
    report = assess_pipeline(
        pulse("srv-worker-1", at(-pulse_age_seconds * SECOND)), None, 0, NOW
    )

    assert report.status is expected
    assert report.checks.worker.pulse_age_seconds == pulse_age_seconds
    assert int(report.checks.worker.limit_seconds) == 300


@pytest.mark.parametrize(
    ("wait_seconds", "expected"),
    [(120, PipelineState.FLOWING), (121, PipelineState.STALLED)],
)
def test_the_inbound_check_allows_two_minutes(
    wait_seconds: int, expected: PipelineState
) -> None:
    waiting = job(QueuedJobStatus.PENDING, JobLane.INBOUND, at(-wait_seconds * SECOND))

    report = assess_pipeline(pulse("srv-worker-1", NOW), waiting, 1, NOW)

    assert report.status is expected
    assert report.checks.worker.status is HealthCheckStatus.OK


def test_no_pulse_at_all_is_stalled() -> None:
    report = health(WatchWorld())

    assert report.status is PipelineState.STALLED
    assert report.checks.worker.status is HealthCheckStatus.FAILED
    assert report.checks.worker.pulse_age_seconds is None
    assert report.checks.inbound.status is HealthCheckStatus.OK


def test_a_batch_worker_pulse_does_not_hide_a_waiting_customer() -> None:
    world = WatchWorld()
    world.worker_beats("srv-batch-worker-1")
    world.customer_waits_since(400)

    report = health(world)

    assert report.status is PipelineState.STALLED
    assert report.checks.worker.status is HealthCheckStatus.OK
    assert report.checks.inbound.status is HealthCheckStatus.FAILED


def test_a_moment_in_the_future_is_zero_seconds_ago() -> None:
    assert seconds_since(at(5 * SECOND), NOW) == 0


class UnreadablePulses(WorkerHeartbeatRepository):
    def find_freshest(self) -> WorkerHeartbeatDocument | None:
        raise ExternalServiceError("The database is unreachable.")


def test_a_database_that_cannot_tell_is_stalled() -> None:
    world = WatchWorld()
    world.worker_beats()

    report = CheckPipelineHealthUseCase(
        UnreadablePulses(world.pulses), world.health_repo, world.clock.wall_clock
    ).run(PipelineHealthQuery())

    assert report.status is PipelineState.STALLED
    assert report.checks.worker.status is HealthCheckStatus.FAILED
    assert report.checks.inbound.status is HealthCheckStatus.FAILED


class FixedPipeline:
    """The route's operator: a ready report, or one that blocks until released."""

    def __init__(
        self, report: PipelineHealthReport, gate: threading.Event | None = None
    ) -> None:
        self._report: PipelineHealthReport = report
        self._gate: threading.Event | None = gate

    def operate(self, input_data: PipelineHealthQuery) -> PipelineHealthReport:
        del input_data
        if self._gate is not None:
            self._gate.wait(timeout=5)
        return self._report


def route_client(operator: FixedPipeline) -> TestClient:
    application = FastAPI()
    application.include_router(build_pipeline_health_router(operator))
    return TestClient(application)


def test_flowing_answers_200_and_stalled_503_never_cached() -> None:
    flowing = assess_pipeline(pulse("srv-worker-1", NOW), None, 0, NOW)
    stalled = assess_pipeline(None, None, 0, NOW)

    ok = route_client(FixedPipeline(flowing)).get("/healthz/pipeline")
    failing = route_client(FixedPipeline(stalled)).get("/healthz/pipeline")

    assert ok.status_code == 200
    assert ok.headers["cache-control"] == "no-store"
    assert ok.json()["status"] == "flowing"
    assert ok.json()["checks"]["worker"] == {
        "status": "ok",
        "pulse_age_seconds": 0,
        "limit_seconds": 300,
    }
    assert failing.status_code == 503
    assert failing.headers["cache-control"] == "no-store"
    assert failing.json()["status"] == "stalled"
    assert "pulse_age_seconds" not in failing.json()["checks"]["worker"]


def test_a_check_that_takes_too_long_answers_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline_health_routes, "PIPELINE_DEADLINE_SECONDS", 0.2)
    gate = threading.Event()
    flowing = assess_pipeline(pulse("srv-worker-1", NOW), None, 0, NOW)
    try:
        response = route_client(FixedPipeline(flowing, gate)).get("/healthz/pipeline")
    finally:
        gate.set()

    assert response.status_code == 503
    assert response.json()["status"] == "stalled"


def test_the_application_serves_it_without_a_token_and_does_not_describe_it() -> None:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings({}))
    client = TestClient(build_application(container))

    response = client.get("/healthz/pipeline")
    description = client.get("/openapi.json").json()

    # The in-memory world without a worker: nothing pulses.
    assert response.status_code == 503
    assert response.json()["checks"]["worker"]["status"] == "failed"
    assert "/healthz/pipeline" not in description["paths"]


def test_the_freshest_pulse_of_two_workers_counts() -> None:
    world = WatchWorld()
    stale = pulse("srv-worker-1", Microseconds(int(NOW) - 600 * SECOND))
    world.pulses.upsert(str(stale.id), stale)
    world.worker_beats("srv-worker-2")

    assert health(world).status is PipelineState.FLOWING
