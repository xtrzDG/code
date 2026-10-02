"""
p95 budgets of the requests people wait for, over a seeded database
(PERF_SCALE; the weekly run uses `full`: 500 businesses, 2M messages,
200k bookings). Each request kind runs 20 untimed and 200 timed times,
spread over the businesses of the manifest; the budget is the p95 in ms
of the whole request through the application (no network).
"""

from collections.abc import Callable
from datetime import timedelta

import pytest

from app.schemas.dto.load_data import LoadBusinessSeed
from tests.e2e.harness_settings import START
from tests.perf.conftest import PerfTarget
from tests.perf.latency import PerfReport, measure

pytestmark = pytest.mark.perf

# p95 in milliseconds. The weekly run also compares against the stored
# baseline (perf/baseline.json): more than 20% slower fails it.
BUDGETS_MS: dict[str, float] = {
    "authenticate": 25.0,
    "conversations_list": 150.0,
    "conversation_detail": 150.0,
    "availability": 120.0,
    "dashboard": 300.0,
    "widget_poll": 60.0,
}
AVAILABILITY_DAYS: int = 14

# A request of one kind, its index spreading it over the dataset: the status.
type Send = Callable[[PerfTarget, int], int]


def business(target: PerfTarget, index: int) -> LoadBusinessSeed:
    businesses: list[LoadBusinessSeed] = target.manifest.businesses
    return businesses[index % len(businesses)]


def owner(entry: LoadBusinessSeed) -> dict[str, str]:
    return {"Authorization": f"Bearer {entry.owner_access_token}"}


def authenticate(target: PerfTarget, index: int) -> int:
    headers = owner(business(target, index))
    return target.client.get("/v1/me", headers=headers).status_code


def conversations_list(target: PerfTarget, index: int) -> int:
    entry = business(target, index)
    return target.client.get(
        f"/v1/businesses/{entry.business_id}/conversations", headers=owner(entry)
    ).status_code


def conversation_detail(target: PerfTarget, index: int) -> int:
    entry = business(target, index)
    rounds: int = index // len(target.manifest.businesses)
    conversation_id = entry.conversation_ids[rounds % len(entry.conversation_ids)]
    return target.client.get(
        f"/v1/businesses/{entry.business_id}/conversations/{conversation_id}",
        headers=owner(entry),
    ).status_code


def availability(target: PerfTarget, index: int) -> int:
    entry = business(target, index)
    day = (START + timedelta(days=index % AVAILABILITY_DAYS)).date().isoformat()
    return target.client.get(
        f"/v1/businesses/{entry.business_id}/availability",
        params={"date": day, "party_size": "2"},
        headers=owner(entry),
    ).status_code


def dashboard(target: PerfTarget, index: int) -> int:
    entry = business(target, index)
    return target.client.get(
        f"/v1/businesses/{entry.business_id}/dashboard", headers=owner(entry)
    ).status_code


def widget_poll(target: PerfTarget, index: int) -> int:
    visitors = [
        (entry, visitor)
        for entry in target.manifest.businesses
        for visitor in entry.visitors
    ]
    entry, visitor = visitors[index % len(visitors)]
    return target.client.get(
        f"/v1/widget/{entry.business_id}/messages",
        params={"after": str(visitor.latest_message_id)},
        headers={"X-Widget-Session-Key": str(visitor.session_key)},
    ).status_code


REQUESTS: dict[str, Send] = {
    "authenticate": authenticate,
    "conversations_list": conversations_list,
    "conversation_detail": conversation_detail,
    "availability": availability,
    "dashboard": dashboard,
    "widget_poll": widget_poll,
}


@pytest.mark.parametrize("name", list(BUDGETS_MS))
def test_p95_latency_stays_within_its_budget(
    name: str, perf_target: PerfTarget, perf_report: PerfReport
) -> None:
    send: Send = REQUESTS[name]
    durations = measure(lambda index: send(perf_target, index))
    result = perf_report.record(name, durations, BUDGETS_MS[name])

    assert result.p95_ms <= result.budget_ms, (
        f"{name}: p95 {result.p95_ms:.1f} ms over its {result.budget_ms:.0f} ms "
        f"budget (p50 {result.p50_ms:.1f} ms, {perf_target.scale.name} scale)"
    )
