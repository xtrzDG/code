"""
Game day: Meta's Graph API host is black-holed (requests are taken and
never answered). Twenty WhatsApp customers write; the worker answers each,
and each reply waits in the outbox, tried again with backoff (10 s ... 21
minutes) until its eighth attempt fails for good. Within the hour the
platform alerts page OUTBOUND_FAILURES and /status shows WhatsApp and the
other messengers degraded; once Meta answers again new replies go out, the
alert resolves and /status is operational.

docs/operations/runbooks/delivery-failures.md is the runbook this rehearses.
"""

from collections.abc import Generator
from functools import partial
from pathlib import Path

import pytest

from tests.chaos.chaos_world import (
    MINUTE,
    ChaosWorld,
    chaos_world,
    component_levels,
    wait_for,
)
from tests.chaos.fake_providers import ProviderState, fake_providers
from tests.chaos.meta_world import (
    customer_outbox,
    customer_writes,
    seed_whatsapp_restaurant,
)
from tests.storage.postgres_server import ThrowawayPostgresServer

CUSTOMERS: int = 20
OUTBOUND_TITLE: str = "Deliveries fail"
# The watchdog would see the moved clock before the worker's next pulse.
NO_WATCHDOG: dict[str, str] = {"PIPELINE_WATCHDOG_SECONDS": "0"}
MICROSECONDS_PER_SECOND: int = 1_000_000


@pytest.fixture
def meta_world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path: Path,
) -> Generator[tuple[ChaosWorld, ProviderState]]:
    with (
        fake_providers() as (provider_url, providers),
        chaos_world(
            postgres_server,
            migrated_template_database,
            tmp_path,
            seed_whatsapp_restaurant,
            provider_url=provider_url,
        ) as world,
    ):
        yield world, providers


def all_failed_or_waiting(world: ChaosWorld, attempts: int) -> bool:
    """Every reply was tried `attempts` times (or gave up already)."""

    rows = customer_outbox(world)
    return len(rows) >= CUSTOMERS and all(
        row.status == "dead" or row.attempts >= attempts for row in rows
    )


def next_retry_in_seconds(world: ChaosWorld) -> float:
    """How far the latest scheduled retry lies ahead on the world's clock."""

    due = [
        row.next_attempt_at
        for row in customer_outbox(world)
        if row.status == "pending" and row.next_attempt_at is not None
    ]
    latest = max(due) / MICROSECONDS_PER_SECOND
    return max(0.0, latest - world.clock.now_seconds())


def test_a_black_holed_meta_pages_degrades_messengers_and_recovers(
    meta_world: tuple[ChaosWorld, ProviderState],
) -> None:
    world, providers = meta_world
    api = world.start_api(NO_WATCHDOG)
    world.start_worker(NO_WATCHDOG)
    providers.is_meta_black_holed = True

    for index in range(CUSTOMERS):
        customer_writes(world, api, index, "Здравствуйте, есть столик на вечер?")
    wait_for(lambda: all_failed_or_waiting(world, 1), 120, "the first attempts")

    # Each round: the clock reaches the latest retry, every reply is tried.
    for attempt in range(2, 9):
        world.clock.advance(next_retry_in_seconds(world) + 2)
        wait_for(
            partial(all_failed_or_waiting, world, attempt), 120, f"attempt {attempt}"
        )
    assert {row.status for row in customer_outbox(world)} == {"dead"}

    # The next five-minute check of the platform alerts sees them.
    world.clock.advance(5 * MINUTE)
    wait_for(lambda: bool(world.alerts(OUTBOUND_TITLE)), 60, "the alert")
    [firing] = world.alerts(OUTBOUND_TITLE)
    assert firing.headline == f"[SEV2] FIRING: {OUTBOUND_TITLE}"
    levels = component_levels(api)
    assert levels["meta"] in {"degraded", "outage"}
    assert levels["chat"] == "operational"

    # Meta answers again: new replies go out, the hour passes, all clear.
    providers.is_meta_black_holed = False
    customer_writes(world, api, CUSTOMERS, "А на завтра?")
    wait_for(
        lambda: "delivered" in {row.status for row in customer_outbox(world)},
        60,
        "a delivered reply",
    )
    world.clock.advance(61 * MINUTE)
    wait_for(lambda: len(world.alerts(OUTBOUND_TITLE)) == 2, 60, "the recovery")
    assert world.alerts(OUTBOUND_TITLE)[1].headline == (
        f"[SEV2] RESOLVED: {OUTBOUND_TITLE}"
    )
    assert component_levels(api)["meta"] == "operational"
