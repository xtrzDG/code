"""Schedule exceptions: holidays, special hours, validation, dates and tenants."""

from datetime import UTC, datetime

import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.dto.resources import (
    CreateScheduleExceptionCommand,
    DeleteScheduleExceptionCommand,
    ScheduleExceptionInput,
    ScheduleExceptionListQuery,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ScheduleExceptionId
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.resource_helpers import add_exception, add_resource, hours


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
