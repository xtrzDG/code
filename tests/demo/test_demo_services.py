"""The demo salon's stylists perform their own services, and bookings carry value."""

from datetime import UTC, datetime

import pytest
from typed_time_provider import Microseconds

from app.registries.billing.plan_registry import PlanRegistry
from app.registries.demo.demo_dataset_registry import DemoDatasetRegistry
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.demo import DemoBusinessKey
from app.schemas.dto.demo_data import (
    DemoActivityRequest,
    DemoBusinessActivity,
    DemoBusinessFoundation,
    DemoFoundationRequest,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.scheduling.availability import blocked_until
from tests.demo.test_demo_catalog import MICROSECONDS_PER_SECOND, MOMENTS

ACTIVE_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)
SEEDED_AT = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)


def salon_story(
    moment: datetime,
) -> tuple[DemoBusinessFoundation, DemoBusinessActivity]:
    now = Microseconds(int(moment.timestamp()) * MICROSECONDS_PER_SECOND)
    registry = DemoDatasetRegistry(PlanRegistry())
    (foundation,) = [
        foundation
        for foundation in registry.build_foundations(
            DemoFoundationRequest(owner_id=UserId(), staff_id=UserId(), now=now)
        )
        if foundation.key is DemoBusinessKey.BERLIN_SALON
    ]
    activity = registry.build_activity(
        DemoActivityRequest(
            foundation=foundation,
            version_ids=[AssistantVersionId() for _ in foundation.assistant_versions],
            model_id=LlmModelId("gpt-5-mini"),
            now=now,
        )
    )
    return foundation, activity


def test_each_stylist_serves_the_services_of_her_answer() -> None:
    foundation, _ = salon_story(SEEDED_AT)
    titles = {item.id: str(item.title) for item in foundation.knowledge_items}

    served = {
        str(resource.name): sorted(
            titles[item_id] for item_id in resource.serves_item_ids
        )
        for resource in foundation.resources
    }

    assert served == {
        "Lena": ["Ansatzfarbe", "Balayage", "Damenhaarschnitt & Föhnen"],
        "Mehmet": ["Bartpflege & Nassrasur", "Herrenhaarschnitt"],
        "Sofia": [
            "Augenbrauen zupfen & färben",
            "Maniküre mit Shellac",
            "Wimpernlifting",
        ],
    }
    assert {
        int(item.buffer_minutes or 0)
        for item in foundation.knowledge_items
        if item.duration_minutes is not None
    } == {10}


def test_every_salon_booking_names_its_service_and_value() -> None:
    foundation, salon = salon_story(SEEDED_AT)
    prices = {item.id: item.price_minor for item in foundation.knowledge_items}

    assert salon.bookings
    for booking in salon.bookings:
        assert booking.service_item_id is not None
        assert booking.value_minor == prices[booking.service_item_id]
        assert booking.currency_code == "EUR"
        assert booking.buffer_minutes == 10


@pytest.mark.parametrize("moment", MOMENTS[::6], ids=lambda moment: moment.isoformat())
def test_no_two_salon_visits_overlap_with_their_breaks(moment: datetime) -> None:
    _, salon = salon_story(moment)
    active = [b for b in salon.bookings if b.status in ACTIVE_STATUSES]

    for first in active:
        for second in active:
            if first.id == second.id or first.resource_id != second.resource_id:
                continue

            apart = blocked_until(first) <= int(second.starts_at) or (
                blocked_until(second) <= int(first.starts_at)
            )
            assert apart, (first, second)
