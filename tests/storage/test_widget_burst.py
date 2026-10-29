"""
A burst of website visitors while the model is slow cannot take the API
down: 64 widget messages at once, each a 20-second turn
(SCRIPTED_LLM_LATENCY_MS), are accepted at once and answered by the worker,
while the API instance stays ready and the cabinet stays fast. Before the
turns left the request thread, such a burst held every request thread and
database connection of an instance until /readyz failed.
"""

import statistics
import subprocess
import sys
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
import pytest

from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY
from tests.storage.two_process_world import (
    SeededRestaurant,
    free_port,
    process_environment,
    seed_restaurant,
    stop_processes,
    wait_until_ready,
    worker_processes,
)

BURST: int = 64
# A small instance, as in production: a few connections, more threads.
API_CAPACITY: dict[str, str] = {
    "THREADPOOL_SIZE": "16",
    "DB_POOL_SIZE": "8",
    "SCRIPTED_LLM_LATENCY_MS": "20000",
}
CABINET_BUDGET_MS: float = 200.0
# Enough samples for a 95th percentile that is not simply the slowest two
# (of 25 it was: a busy machine pausing the test twice failed it).
SAMPLES: int = 100
SAMPLE_INTERVAL_SECONDS: float = 0.05


@dataclass(frozen=True)
class BurstWorld:
    restaurant: SeededRestaurant
    api_url: str


@pytest.fixture(scope="module")
def burst_world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[BurstWorld]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    database_url = str(postgres_server.app_database_url(database_name))
    directory = tmp_path_factory.mktemp("widget-burst")
    environment = {**process_environment(database_url), **API_CAPACITY}
    port = free_port()
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_application",
            "--factory",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=PROJECT_ROOT_DIRECTORY,
        env=environment,
    )
    try:
        restaurant = seed_restaurant(database_url)
        url = f"http://127.0.0.1:{port}"
        wait_until_ready(api, url)
        # The real worker with the slow scripted model answers the burst.
        with worker_processes(
            database_url, None, directory, extra_environment=API_CAPACITY
        ):
            yield BurstWorld(restaurant, url)
    finally:
        stop_processes([api])
        postgres_server.drop_database(database_name)


def send(world: BurstWorld, index: int) -> httpx.Response:
    return httpx.post(
        f"{world.api_url}/v1/widget/{world.restaurant.business_id}/messages",
        json={
            "session_key": f"visitor_burst_{index:010d}",
            "text": "Do you have a table for four tonight?",
        },
        # Eight visitors per network address, as from a few offices.
        headers={"X-Forwarded-For": f"198.51.100.{index % 8 + 1}"},
        timeout=30,
    )


def sample_cabinet(world: BurstWorld) -> tuple[list[int], list[float]]:
    """/readyz statuses and GET /v1/me times (ms) while the burst runs."""

    statuses: list[int] = []
    timings: list[float] = []
    with httpx.Client(base_url=world.api_url, timeout=10) as client:
        for _ in range(SAMPLES):
            statuses.append(client.get("/readyz").status_code)
            started = time.perf_counter()
            me = client.get("/v1/me", headers=world.restaurant.headers)
            timings.append((time.perf_counter() - started) * 1000)
            assert me.status_code == 200, me.text
            time.sleep(SAMPLE_INTERVAL_SECONDS)

    return statuses, timings


def test_a_burst_of_slow_turns_leaves_the_api_ready_and_fast(
    burst_world: BurstWorld,
) -> None:
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=BURST) as pool:
        accepted = list(pool.map(send, [burst_world] * BURST, range(BURST)))
    accept_seconds = time.monotonic() - started

    # Every message is accepted at once; none waits for its 20 s turn.
    assert [response.status_code for response in accepted] == [202] * BURST
    assert accept_seconds < 15.0

    # The worker now holds 20-second turns; the API serves the cabinet.
    statuses, timings = sample_cabinet(burst_world)

    assert set(statuses) == {200}
    p95 = statistics.quantiles(timings, n=20)[-1]
    described = ", ".join(f"{timing:.0f}" for timing in sorted(timings))
    assert p95 < CABINET_BUDGET_MS, described
    assert statistics.median(timings) < CABINET_BUDGET_MS / 2, described
