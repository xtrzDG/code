"""
Game day: the only worker is killed (SIGKILL, as an OOM kill or a crashed
host does). Two API processes watch the pipeline from outside. Within six
minutes GET /healthz/pipeline answers 503, /status no longer says
operational, and the team gets exactly one WORKER_DOWN message from one
API process (the watchdog's leader, straight through the platform bot).
A new worker brings it all back, and the recovery is told once.

docs/operations/runbooks/worker-down.md is the runbook this rehearses.
"""

import time
from collections.abc import Generator
from functools import partial
from pathlib import Path

import pytest

from tests.chaos.chaos_world import (
    MINUTE,
    WORKER_DOWN_TITLE,
    ChaosWorld,
    chaos_world,
    component_levels,
    pipeline,
    wait_for,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.two_process_world import seed_restaurant

WATCHDOG_EVERY_SECOND: dict[str, str] = {"PIPELINE_WATCHDOG_SECONDS": "1"}
# Long enough for every API process to take several looks.
SETTLE_SECONDS: float = 5.0


@pytest.fixture
def world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path: Path,
) -> Generator[ChaosWorld]:
    with chaos_world(
        postgres_server, migrated_template_database, tmp_path, seed_restaurant
    ) as world:
        yield world


def is_flowing(url: str) -> bool:
    return pipeline(url)[0] == 200


def test_a_killed_worker_pages_once_and_its_return_is_told_once(
    world: ChaosWorld,
) -> None:
    apis = [world.start_api(WATCHDOG_EVERY_SECOND) for _ in range(2)]
    worker = world.start_worker()
    for url in apis:
        wait_for(partial(is_flowing, url), what="a flowing pipeline")
    assert component_levels(apis[0])["chat"] == "operational"

    worker.kill()
    worker.wait()
    # Six minutes pass with no worker at all.
    world.clock.advance(6 * MINUTE)
    wait_for(lambda: not is_flowing(apis[0]), what="GET /healthz/pipeline 503")
    wait_for(
        lambda: bool(world.alerts(WORKER_DOWN_TITLE)), what="the WORKER_DOWN alert"
    )
    # Every API process looks a few more times: none tells it again.
    time.sleep(SETTLE_SECONDS)

    status, body = pipeline(apis[1])
    assert status == 503
    assert body["status"] == "stalled"
    assert body["checks"]["worker"]["status"] == "failed"
    assert int(body["checks"]["worker"]["pulse_age_seconds"]) >= 6 * 60
    [firing] = world.alerts(WORKER_DOWN_TITLE)
    assert firing.headline == f"[SEV1] FIRING: {WORKER_DOWN_TITLE}"
    assert firing.channel == "telegram"
    assert firing.pid in {process.pid for process in world.processes[:2]}
    levels = component_levels(apis[1])
    assert {levels["chat"], levels["meta"], levels["telegram"]} == {"outage"}
    assert levels["cabinet"] == "operational"

    # A new worker: the pipeline flows, the episode ends once.
    world.start_worker()
    for url in apis:
        wait_for(partial(is_flowing, url), what="the pipeline back")
    wait_for(
        lambda: len(world.alerts(WORKER_DOWN_TITLE)) == 2, what="the RESOLVED message"
    )
    time.sleep(SETTLE_SECONDS)

    headlines = [sent.headline for sent in world.alerts(WORKER_DOWN_TITLE)]
    assert headlines == [
        f"[SEV1] FIRING: {WORKER_DOWN_TITLE}",
        f"[SEV1] RESOLVED: {WORKER_DOWN_TITLE}",
    ]
    assert component_levels(apis[0])["chat"] == "operational"
