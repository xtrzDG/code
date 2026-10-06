"""
Game day: Postgres goes away under a running API and worker (an immediate
stop, as a crash or a failover does) and comes back on the same address.
While it is away the outside monitor's two checks fail at once (GET
/readyz and GET /healthz/pipeline answer 503: this is what pages), a
visitor's message is refused rather than silently lost, and neither
process dies. Once it is back both checks pass by themselves, the next
visitor is answered, /status is operational, and nobody was paged by the
watchdog for a restart shorter than its five minutes.

docs/operations/runbooks/database-failover.md is the runbook this
rehearses. The server is this module's own: the other tests' server is
never stopped.
"""

import time
from collections.abc import Generator
from functools import partial
from pathlib import Path

import httpx
import pytest

from tests.chaos.chaos_world import (
    WORKER_DOWN_TITLE,
    ChaosWorld,
    chaos_world,
    component_levels,
    get_json,
    pipeline,
    wait_for,
)
from tests.chaos.widget_visitors import (
    assistant_answers,
    session_key,
    visitor_writes,
)
from tests.storage.conftest import create_migrated_database
from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    is_postgres_available,
    postgres_bin_directory,
)
from tests.storage.two_process_world import seed_restaurant

WATCHDOG_EVERY_SECOND: dict[str, str] = {"PIPELINE_WATCHDOG_SECONDS": "1"}
QUESTION: str = "Здравствуйте! Вы работаете завтра вечером?"
BACKLOG_TITLE: str = "Customer messages wait"
# Long enough for every process to try the database many times.
OUTAGE_SECONDS: float = 8.0
WIDGET_POLL: float = 3.0
HTTP_SERVICE_UNAVAILABLE: int = 503
HTTP_SERVER_ERROR: int = 500


@pytest.fixture(scope="module")
def restartable_postgres() -> Generator[tuple[ThrowawayPostgresServer, str]]:
    bin_directory = postgres_bin_directory()
    if not is_postgres_available(bin_directory):
        pytest.skip(f"Postgres binaries not found in {bin_directory}.")

    server = ThrowawayPostgresServer(bin_directory)
    server.start()
    try:
        yield server, create_migrated_database(server)
    finally:
        server.stop()


@pytest.fixture
def world(
    restartable_postgres: tuple[ThrowawayPostgresServer, str], tmp_path: Path
) -> Generator[ChaosWorld]:
    server, template = restartable_postgres
    with chaos_world(server, template, tmp_path, seed_restaurant) as world:
        yield world


def is_ready(url: str) -> bool:
    return get_json(url, "/readyz")[0] == 200


def is_flowing(url: str) -> bool:
    return pipeline(url)[0] == 200


def is_answered(world: ChaosWorld, api_url: str, index: int) -> bool:
    return bool(assistant_answers(world, api_url, index))


def test_a_restarted_database_pages_outside_and_everything_comes_back(
    world: ChaosWorld,
) -> None:
    worker = world.start_worker()
    api = world.start_api(WATCHDOG_EVERY_SECOND)
    wait_for(partial(is_flowing, api), what="a flowing pipeline")
    visitor_writes(world, api, 0, QUESTION)
    wait_for(partial(is_answered, world, api, 0), 60, "the first answer", WIDGET_POLL)

    world.postgres_server.pause()
    # The outside monitor's two checks fail at once.
    readiness, report = get_json(api, "/readyz")
    assert readiness == HTTP_SERVICE_UNAVAILABLE
    assert report["checks"]["database"]["status"] == "failed"
    status, body = pipeline(api)
    assert status == HTTP_SERVICE_UNAVAILABLE
    assert body["status"] == "stalled"
    # A visitor's message is refused (the widget sends it again), not lost.
    refused = httpx.post(
        f"{api}/v1/widget/{world.restaurant.business_id}/messages",
        json={"session_key": session_key(1), "text": QUESTION},
        timeout=30,
    )
    assert refused.status_code >= HTTP_SERVER_ERROR
    time.sleep(OUTAGE_SECONDS)
    assert worker.poll() is None
    assert all(process.poll() is None for process in world.processes)

    world.postgres_server.resume()
    # Nobody restarts anything: the pools reconnect by themselves.
    wait_for(partial(is_ready, api), 60, "GET /readyz 200")
    wait_for(partial(is_flowing, api), 60, "GET /healthz/pipeline 200")
    visitor_writes(world, api, 1, QUESTION)
    wait_for(partial(is_answered, world, api, 1), 60, "the next answer", WIDGET_POLL)
    assert component_levels(api)["chat"] == "operational"
    # Shorter than the watchdog's five minutes: the monitor paged, not it.
    assert world.alerts(WORKER_DOWN_TITLE) == []
    assert world.alerts(BACKLOG_TITLE) == []
