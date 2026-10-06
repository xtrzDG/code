"""
The service levels on the real application: every answered request but
the probes counts for the API availability SLI, the counts reach the
shared slots when the process flushes them, `record_sli` folds them into
the hour's row, and only platform admins read the error budget.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.service_levels import ServiceLevelSlotDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import JobName
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import sign_in_and_create_restaurant

type JsonObject = dict[str, Any]

BUDGET_URL: str = "/v1/admin/system/error-budget"
HOUR_SECONDS: int = 60 * 60
API: ServiceLevelSeries = ServiceLevelSeries.API_AVAILABILITY


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop()
    with running.client:
        yield running


def api_slots(workshop: Workshop) -> list[ServiceLevelSlotDocument]:
    slots = workshop.container.repositories.service_level_slot_repo()
    return slots.list_window(API, Microseconds(0), Microseconds(2**62))


def record_service_levels(workshop: Workshop) -> None:
    operator = workshop.container.operators.telemetry.record_service_levels_operator()
    operator.operate(
        JobTick(job_name=JobName("record_sli"), scheduled_at=Microseconds(0))
    )


def test_answered_requests_reach_the_slots_but_probes_do_not(
    workshop: Workshop,
) -> None:
    tally = workshop.container.gateways.api_availability_tally()
    tally.flush()  # whatever the start of the application asked
    before = sum(int(slot.total) for slot in api_slots(workshop))

    for _ in range(3):
        assert workshop.client.get("/healthz").status_code == 200
    assert workshop.client.get("/v1/legal/subprocessors").status_code == 200
    assert workshop.client.get(BUDGET_URL).status_code == 401
    tally.flush()

    slots = api_slots(workshop)
    assert sum(int(slot.total) for slot in slots) == before + 2
    assert all(int(slot.good) == int(slot.total) for slot in slots)


def test_the_error_budget_reads_the_rows_record_sli_wrote(
    workshop: Workshop,
) -> None:
    owner_token, _, _ = sign_in_and_create_restaurant(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    workshop.container.gateways.api_availability_tally().flush()
    requests = sum(int(slot.total) for slot in api_slots(workshop))
    workshop.clock.advance(HOUR_SECONDS + 15 * 60)
    record_service_levels(workshop)

    refused = workshop.client.get(BUDGET_URL, headers=bearer(owner_token))
    answered = workshop.client.get(BUDGET_URL, headers=bearer(admin_token))

    assert refused.status_code == 403, refused.text
    assert answered.status_code == 200, answered.text
    view: JsonObject = answered.json()
    by_series = {item["series"]: item for item in view["objectives"]}
    assert set(by_series) == {series.value for series in ServiceLevelSeries}
    assert by_series[API.value]["events"] == requests > 0
    assert by_series[API.value]["budget_left_permille"] == 1000
    assert by_series[API.value]["objective"] == 0.999
    assert view["latency"]["target_ms"] == 15_000
    assert view["measured_since"] is not None
    assert view["measured_until"] > view["measured_since"]
