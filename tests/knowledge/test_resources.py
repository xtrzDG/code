"""Resources: niche defaults, rules, patches, listing and tenant isolation."""

from datetime import UTC, datetime

import pytest

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.resources import (
    CreateResourceCommand,
    CreateScheduleExceptionCommand,
    ResourceInput,
    ResourceListQuery,
    ResourcePatch,
    ScheduleExceptionInput,
    UpdateResourceCommand,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.resource_helpers import add_exception, add_resource, hours


def test_resources_default_to_the_niche_kind_and_booking_unit() -> None:
    harness = KnowledgeHarness()
    restaurant = harness.add_business(niche_key=NicheKey.RESTAURANT)
    hotel = harness.add_business(niche_key=NicheKey.HOTEL)

    table = add_resource(harness, restaurant, " Table 4 ")
    room = add_resource(
        harness,
        hotel,
        "Double room",
        unit_count=ResourceUnitCount(6),
    )

    assert table.name == " Table 4 "
    assert table.kind is ResourceKind.TABLE
    assert table.booking_unit is BookingUnit.TIME_SLOT
    assert table.schedule == []
    assert room.kind is ResourceKind.ROOM
    assert room.booking_unit is BookingUnit.NIGHT
    assert room.unit_count == 6


def test_resource_rules() -> None:
    harness = KnowledgeHarness()
    hotel = harness.add_business(niche_key=NicheKey.HOTEL)
    salon = harness.add_business(niche_key=NicheKey.BEAUTY_SALON)
    add_resource(harness, salon, "Nino")

    with pytest.raises(ValidationFailedError, match="by nights"):
        add_resource(harness, hotel, "Suite", slot_minutes=SlotDurationMinutes(60))
    with pytest.raises(ConflictError, match="already exists"):
        add_resource(harness, salon, "NINO")
    with pytest.raises(ValidationFailedError, match="name"):
        add_resource(harness, salon, "   ")
    with pytest.raises(ValidationFailedError, match="overlap"):
        add_resource(
            harness,
            salon,
            "Mariam",
            schedule=[
                hours(Weekday.MONDAY, 600, 900),
                hours(Weekday.MONDAY, 800, 1000),
            ],
        )

    master = add_resource(
        harness,
        salon,
        "Mariam",
        slot_minutes=SlotDurationMinutes(45),
        schedule=[hours(Weekday.TUESDAY, 600, 1080), hours(Weekday.MONDAY, 600, 1080)],
    )
    assert [interval.weekday for interval in master.schedule] == [
        Weekday.MONDAY,
        Weekday.TUESDAY,
    ]
    assert master.slot_minutes == 45


def test_patch_updates_deactivates_and_keeps_names_unique() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.ENTERTAINMENT)
    arena = add_resource(harness, business, "VR arena 1")
    add_resource(harness, business, "VR arena 2")
    harness.clock_source.set(datetime(2026, 10, 3, 9, 0, tzinfo=UTC))

    updated = harness.update_resource.run(
        UpdateResourceCommand(
            business_id=business.id,
            resource_id=arena.id,
            patch=ResourcePatch.model_validate_json(
                '{"capacity": 6, "is_active": false, "slot_minutes": 90}'
            ),
        )
    )

    assert updated.capacity == 6
    assert updated.is_active is False
    assert updated.slot_minutes == 90
    assert updated.name == "VR arena 1"
    assert updated.updated_at > arena.updated_at

    with pytest.raises(ConflictError):
        harness.update_resource.run(
            UpdateResourceCommand(
                business_id=business.id,
                resource_id=arena.id,
                patch=ResourcePatch(name=ResourceName("vr arena 2")),
            )
        )
    with pytest.raises(ValidationFailedError, match="null"):
        harness.update_resource.run(
            UpdateResourceCommand(
                business_id=business.id,
                resource_id=arena.id,
                patch=ResourcePatch.model_validate_json('{"capacity": null}'),
            )
        )

    renamed = harness.update_resource.run(
        UpdateResourceCommand(
            business_id=business.id,
            resource_id=arena.id,
            patch=ResourcePatch(name=ResourceName("VR arena 1")),
        )
    )
    assert renamed.name == "VR arena 1"

    nightly = harness.update_resource.run(
        UpdateResourceCommand(
            business_id=business.id,
            resource_id=arena.id,
            patch=ResourcePatch(booking_unit=BookingUnit.NIGHT),
        )
    )
    assert nightly.slot_minutes is None


def test_list_filters_and_orders_resources() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    add_resource(harness, business, "Table 2")
    add_resource(harness, business, "Table 10", is_active=False)
    add_resource(harness, business, "Bar", kind=ResourceKind.SLOT)

    everything = harness.list_resources.run(ResourceListQuery(business_id=business.id))
    active = harness.list_resources.run(
        ResourceListQuery(business_id=business.id, is_active=True)
    )

    assert [item.name for item in everything.items] == ["Bar", "Table 10", "Table 2"]
    assert [item.name for item in active.items] == ["Bar", "Table 2"]


def test_resources_of_another_business_are_invisible() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    other = harness.add_business()
    table = add_resource(harness, business, "Table 1")

    with pytest.raises(NotFoundError):
        harness.update_resource.run(
            UpdateResourceCommand(
                business_id=other.id,
                resource_id=table.id,
                patch=ResourcePatch(is_active=False),
            )
        )
    with pytest.raises(NotFoundError, match="Resource"):
        add_exception(harness, other, "2026-12-31", resource_id=table.id)
    assert (
        harness.list_resources.run(ResourceListQuery(business_id=other.id)).items == []
    )


def test_unknown_business_cannot_get_resources_or_exceptions() -> None:
    harness = KnowledgeHarness()

    with pytest.raises(NotFoundError):
        harness.create_resource.run(
            CreateResourceCommand(
                business_id=BusinessId(),
                resource=ResourceInput(
                    name=ResourceName("Table"),
                    capacity=ResourceCapacity(2),
                ),
            )
        )
    with pytest.raises(NotFoundError):
        harness.create_schedule_exception.run(
            CreateScheduleExceptionCommand(
                business_id=BusinessId(),
                exception=ScheduleExceptionInput(date=LocalDate("2026-12-31")),
            )
        )
