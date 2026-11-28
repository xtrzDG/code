"""
The status page's payments component (REL-06): degraded by a payment
reconciliation mismatch or failing storage, and written into the day
records and the announcements now that its release gate is open (the
release before, launch-2026-11-05, reads the value).
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    StatusComponent,
    StatusLevel,
)
from app.schemas.dto.platform_announcements import (
    CreateAnnouncementBody,
    UpdateAnnouncementBody,
)
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform_status.constrained_strings import StatusDay
from app.use_cases.platform_status.gated_components import (
    require_announceable,
    stored_components,
)
from app.use_cases.platform_status.status_history import fold_levels
from app.utilities.storage.release_gates import RELEASE_GATES, is_gate_open
from app.utilities.storage.status_release_gates import (
    PAYMENTS_STATUS_GATE,
    STATUS_RELEASE_GATES,
)
from tests.platform_status.status_world import StatusWorld
from tests.platform_status.test_announcements import ENGLISH, create, update
from tests.platform_status.test_platform_status import component, record, status

CLOSED: tuple[ReleaseGate, ...] = tuple(
    gate.model_copy(update={"is_open": False}) for gate in STATUS_RELEASE_GATES
)
PAYMENTS = [StatusComponent.PAYMENTS]


def test_the_gate_is_open_in_this_release() -> None:
    assert is_gate_open(PAYMENTS_STATUS_GATE) is True
    assert all(gate in RELEASE_GATES for gate in STATUS_RELEASE_GATES)
    assert stored_components() == tuple(StatusComponent)
    assert StatusComponent.PAYMENTS not in stored_components(CLOSED)


@pytest.mark.parametrize(
    ("code", "level"),
    [
        (PlatformAlertCode.PAYMENT_MISMATCH, StatusLevel.DEGRADED),
        (PlatformAlertCode.STORAGE_ERRORS, StatusLevel.DEGRADED),
        (PlatformAlertCode.LLM_ERRORS, StatusLevel.OPERATIONAL),
    ],
)
def test_the_page_shows_payments_from_the_alerts_that_affect_them(
    code: PlatformAlertCode, level: StatusLevel
) -> None:
    world = StatusWorld()
    world.fire(code, 3)

    view = status(world)

    assert component(view, StatusComponent.PAYMENTS) is level
    [payments] = [
        row for row in view.components if row.component is StatusComponent.PAYMENTS
    ]
    assert [day.level for day in payments.history[:-1]] == [StatusLevel.NO_DATA] * (
        len(payments.history) - 1
    )
    assert payments.history[-1].level is level


def test_the_job_records_the_payments_day_now_the_gate_is_open() -> None:
    world = StatusWorld()
    world.fire(PlatformAlertCode.PAYMENT_MISMATCH, 2)

    record(world)

    [day] = world.days.list_all()
    [payments] = [
        row for row in day.components if row.component is StatusComponent.PAYMENTS
    ]
    assert payments.worst_level is StatusLevel.DEGRADED


def test_this_release_records_payments_days() -> None:
    day = fold_levels(
        None,
        StatusDay("2026-11-02"),
        {StatusComponent.PAYMENTS: StatusLevel.DEGRADED},
        Microseconds(1_790_000_000_000_000),
    )

    [payments] = [
        row for row in day.components if row.component is StatusComponent.PAYMENTS
    ]
    assert payments.worst_level is StatusLevel.DEGRADED
    assert int(payments.degraded_count) == 1


def test_an_announcement_names_payments_now_the_gate_is_open() -> None:
    world = StatusWorld()
    body = CreateAnnouncementBody(
        level=AnnouncementLevel.OUTAGE, components=PAYMENTS, messages=ENGLISH
    )

    create(world, body)
    created = create(
        world, body.model_copy(update={"components": [StatusComponent.CHAT]})
    )
    update(world, created.id, UpdateAnnouncementBody(components=PAYMENTS))

    assert [row.components for row in world.announcements.list_all()] == [
        PAYMENTS,
        PAYMENTS,
    ]
    require_announceable(PAYMENTS)
    with pytest.raises(ValidationFailedError, match="payments"):
        require_announceable(PAYMENTS, CLOSED)
