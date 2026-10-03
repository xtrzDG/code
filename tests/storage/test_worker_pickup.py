"""
A customer message accepted by an API process is taken by a separate
worker process within half a second: the queue's NOTIFY wakes the worker's
lane threads (their polls are set to a minute here, so nothing else could),
and the worker logs the wait as `pickup_delay_ms`.
"""

import json
import time
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.two_process_world import (
    SeededRestaurant,
    api_processes,
    seed_restaurant,
    worker_processes,
)

PICKUP_LIMIT_MS: int = 500
WAIT_SECONDS: float = 30.0
# A minute: a pickup within the limit can only come from the wake-up.
SLOW_POLLS: dict[str, str] = {
    "WORKER_POLL_SECONDS": "60",
    "WORKER_INBOUND_POLL_SECONDS": "60",
}
VISITORS: tuple[str, ...] = (
    "visitor_pickup_00000001",
    "visitor_pickup_00000002",
    "visitor_pickup_00000003",
)


@dataclass(frozen=True)
class PickupWorld:
    restaurant: SeededRestaurant
    api_url: str
    worker_log: Path
    postgres_server: ThrowawayPostgresServer
    database_name: str


@pytest.fixture(scope="module")
def pickup_world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[PickupWorld]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    database_url = str(postgres_server.app_database_url(database_name))
    directory = tmp_path_factory.mktemp("worker-pickup")
    call_log = directory / "model-calls.log"
    try:
        restaurant = seed_restaurant(database_url)
        with (
            api_processes(database_url, call_log, count=1) as urls,
            worker_processes(
                database_url, call_log, directory, extra_environment=SLOW_POLLS
            ) as logs,
        ):
            world = PickupWorld(
                restaurant, urls[0], logs[0], postgres_server, database_name
            )
            wait_until_the_worker_listens(world)
            yield world
    finally:
        postgres_server.drop_database(database_name)


def wait_until_the_worker_listens(world: PickupWorld) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        with world.postgres_server.admin_connection(world.database_name) as connection:
            row = connection.execute(
                "select count(*) from pg_stat_activity "
                "where application_name = 'assistant-workshop-job-wakeup' "
                "and query ilike 'listen%%'"
            ).fetchone()
        if row is not None and int(row[0]) > 0:
            # Let the first claims and the reconnect wake-up settle.
            time.sleep(1.0)
            return
        time.sleep(0.1)

    raise AssertionError("The worker never started listening for wake-ups.")


def pickups(worker_log: Path) -> list[dict[str, object]]:
    """The worker's pickup lines of customer messages, oldest first."""

    lines: list[dict[str, object]] = []
    for raw in worker_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.startswith("{"):
            continue
        entry: dict[str, object] = json.loads(raw)
        if (
            "pickup_delay_ms" in entry
            and entry.get("job_name") == "process_inbound_message"
        ):
            lines.append(entry)

    return lines


def wait_for_pickups(world: PickupWorld, count: int) -> list[dict[str, object]]:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        found = pickups(world.worker_log)
        if len(found) >= count:
            return found
        time.sleep(0.05)

    return pickups(world.worker_log)


def send(world: PickupWorld, session_key: str, text: str) -> httpx.Response:
    return httpx.post(
        f"{world.api_url}/v1/widget/{world.restaurant.business_id}/messages",
        json={"session_key": session_key, "text": text},
        timeout=30,
    )


def test_the_worker_takes_an_api_message_within_half_a_second(
    pickup_world: PickupWorld,
) -> None:
    for index, visitor in enumerate(VISITORS):
        before = len(pickups(pickup_world.worker_log))
        sent_at = time.monotonic()
        accepted = send(pickup_world, visitor, f"Do you have a table at {18 + index}?")

        assert accepted.status_code == 202, accepted.text
        assert accepted.json()["event_id"].startswith("inbound_event_")
        found = wait_for_pickups(pickup_world, before + 1)
        assert len(found) == before + 1, "the worker did not take the message"
        assert time.monotonic() - sent_at < 5.0
        delay = found[-1]["pickup_delay_ms"]
        assert isinstance(delay, int)
        assert delay < PICKUP_LIMIT_MS, found[-1]
        assert found[-1]["lane"] == "inbound"


def test_the_widget_polls_the_workers_answer(pickup_world: PickupWorld) -> None:
    session_key = "visitor_pickup_answer_01"
    headers = {"X-Widget-Session-Key": session_key}
    business_id = pickup_world.restaurant.business_id
    url = f"{pickup_world.api_url}/v1/widget/{business_id}/messages"

    assert send(pickup_world, session_key, "Is the terrace open?").status_code == 202
    deadline = time.monotonic() + WAIT_SECONDS
    cursor: str | None = None
    texts: list[str] = []
    while not texts and time.monotonic() < deadline:
        page = httpx.get(
            url, headers=headers, params={"after": cursor or ""}, timeout=10
        ).json()
        cursor = page.get("cursor") or cursor
        texts = [
            item["text"] for item in page["items"] if item["author"] == "assistant"
        ]
        time.sleep(0.3)

    # The first answer starts with the AI disclosure.
    [answer] = texts
    assert answer.endswith("Спасибо! Сейчас уточню и отвечу.")
