from datetime import UTC, datetime

import pytest

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.resources import (
    CreateResourceCommand,
    CreateScheduleExceptionCommand,
    DeleteScheduleExceptionCommand,
    ResourceInput,
    ResourceListQuery,
    ResourcePatch,
    ResourceView,
    ScheduleExceptionInput,
    ScheduleExceptionListQuery,
    ScheduleExceptionView,
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
from app.schemas.typings.bookings.prefixed_id import ResourceId, ScheduleExceptionId
from app.schemas.typings.bookings.strings import ResourceName, ScheduleExceptionNote
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.knowledge.harness import KnowledgeHarness


def hours(weekday: Weekday, opens: int, closes: int) -> OpeningInterval:
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(opens),
        closes_at=ClosingMinuteOfDay(closes),
    )


def add_resource(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    name: str,
    **fields: object,
) -> ResourceView:
    resource_input = ResourceInput.model_validate(
        {"name": ResourceName(name), "capacity": ResourceCapacity(4), **fields}
    )
    return harness.create_resource.run(
        CreateResourceCommand(business_id=business.id, resource=resource_input)
    )


def add_exception(
    harness: KnowledgeHarness,
    business: BusinessDocument,
    date: str,
    resource_id: ResourceId | None = None,
    special_hours: list[OpeningInterval] | None = None,
    note: str | None = None,
) -> ScheduleExceptionView:
    return harness.create_schedule_exception.run(
        CreateScheduleExceptionCommand(
            business_id=business.id,
            exception=ScheduleExceptionInput(
                resource_id=resource_id,
                date=LocalDate(date),
                is_closed_all_day=special_hours is None,
                special_hours=special_hours or [],
                note=None if note is None else ScheduleExceptionNote(note),
            ),
        )
    )


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


def test_schedule_exceptions_for_holidays_and_special_hours() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    table = add_resource(harness, business, "Table 1")

    christmas = add_exception(
        harness,
        business,
        "2027-01-07",
        note="  Orthodox Christmas  ",
    )
    new_year_eve = add_exception(
        harness,
        business,
        "2026-12-31",
        special_hours=[hours(Weekday.THURSDAY, 720, 1440)],
    )
    table_closed = add_exception(harness, business, "2026-12-31", resource_id=table.id)

    assert christmas.is_closed_all_day is True
    assert christmas.weekday is Weekday.THURSDAY
    assert christmas.note == "  Orthodox Christmas  "
    assert new_year_eve.special_hours[0].closes_at == 1440
    assert table_closed.resource_id == table.id

    listed = harness.list_schedule_exceptions.run(
        ScheduleExceptionListQuery(business_id=business.id)
    )
    assert [item.date for item in listed.items] == [
        "2026-12-31",
        "2026-12-31",
        "2027-01-07",
    ]
    for_table = harness.list_schedule_exceptions.run(
        ScheduleExceptionListQuery(
            business_id=business.id,
            resource_id=table.id,
            from_date=LocalDate("2027-01-01"),
        )
    )
    assert [item.id for item in for_table.items] == [christmas.id]


@pytest.mark.parametrize(
    ("date", "special_hours", "error", "message"),
    [
        ("2026-02-30", None, ValidationFailedError, "not a calendar date"),
        ("2026-09-30", None, ValidationFailedError, "already past"),
        (
            "2026-12-31",
            [hours(Weekday.FRIDAY, 600, 900)],
            ValidationFailedError,
            "must be on thursday",
        ),
    ],
)
def test_invalid_schedule_exceptions_are_rejected(
    date: str,
    special_hours: list[OpeningInterval] | None,
    error: type[Exception],
    message: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(error, match=message):
        add_exception(harness, business, date, special_hours=special_hours)


def test_closed_day_with_hours_and_open_day_without_hours_are_rejected() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="closed day cannot"):
        harness.create_schedule_exception.run(
            CreateScheduleExceptionCommand(
                business_id=business.id,
                exception=ScheduleExceptionInput(
                    date=LocalDate("2026-12-31"),
                    is_closed_all_day=True,
                    special_hours=[hours(Weekday.THURSDAY, 600, 900)],
                ),
            )
        )
    with pytest.raises(ValidationFailedError, match="needs special hours"):
        harness.create_schedule_exception.run(
            CreateScheduleExceptionCommand(
                business_id=business.id,
                exception=ScheduleExceptionInput(
                    date=LocalDate("2026-12-31"),
                    is_closed_all_day=False,
                ),
            )
        )


def test_one_exception_per_day_and_scope() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    add_exception(harness, business, "2026-12-31")

    with pytest.raises(ConflictError, match="already has"):
        add_exception(harness, business, "2026-12-31")


@pytest.mark.parametrize(
    ("timezone", "is_accepted"),
    [
        ("Asia/Tbilisi", False),
        ("Asia/Tokyo", False),
        ("America/New_York", True),
        ("Pacific/Honolulu", True),
    ],
)
def test_past_dates_are_judged_in_the_business_time_zone(
    timezone: str,
    is_accepted: bool,
) -> None:
    harness = KnowledgeHarness()
    harness.clock_source.set(datetime(2026, 10, 1, 22, 30, tzinfo=UTC))
    business = harness.add_business(timezone=timezone)

    if is_accepted:
        assert add_exception(harness, business, "2026-10-01").date == "2026-10-01"
    else:
        with pytest.raises(ValidationFailedError, match="already past"):
            add_exception(harness, business, "2026-10-01")


def test_delete_schedule_exception_is_tenant_scoped() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    other = harness.add_business()
    holiday = add_exception(harness, business, "2026-11-23")

    with pytest.raises(NotFoundError):
        harness.delete_schedule_exception.run(
            DeleteScheduleExceptionCommand(
                business_id=other.id, exception_id=holiday.id
            )
        )
    deletion = harness.delete_schedule_exception.run(
        DeleteScheduleExceptionCommand(business_id=business.id, exception_id=holiday.id)
    )

    assert deletion.id == holiday.id
    assert (
        harness.list_schedule_exceptions.run(
            ScheduleExceptionListQuery(business_id=business.id)
        ).items
        == []
    )
    with pytest.raises(NotFoundError):
        harness.delete_schedule_exception.run(
            DeleteScheduleExceptionCommand(
                business_id=business.id,
                exception_id=ScheduleExceptionId(),
            )
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
