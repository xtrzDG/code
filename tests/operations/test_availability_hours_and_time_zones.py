"""Availability around holidays, special and overnight hours, offsets and DST gaps."""

from datetime import datetime

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.dto.bookings import AvailabilityQuery
from app.schemas.typings.bookings.constrained_strings import LocalDate
from tests.operations.availability_fixtures import RestaurantFixture, times
from tests.operations.builders import every_day, interval
from tests.operations.operations_world import OperationsWorld


def test_holiday_and_special_hours() -> None:
    restaurant = RestaurantFixture()
    restaurant.world.add_exception(restaurant.business, "2026-10-06")
    restaurant.world.add_exception(
        restaurant.business,
        "2026-10-07",
        special_hours=[interval(Weekday.WEDNESDAY, "12:00", "16:00")],
    )

    holiday = restaurant.query(day="2026-10-06")
    short_day = restaurant.query(day="2026-10-07")

    assert not holiday.is_open_on_date
    assert holiday.slots == []
    assert short_day.is_open_on_date
    assert times(short_day) == ["12:00", "12:30", "13:00", "13:30", "14:00"]


def test_overnight_bar_offers_slots_after_midnight() -> None:
    world = OperationsWorld(datetime.fromisoformat("2026-10-05T08:00:00+00:00"))
    bar = world.add_business(
        name="Bar Notte",
        country_code="IT",
        timezone="Europe/Rome",
        currency_code="EUR",
        languages=("it", "en"),
        owner_language="it",
    )
    world.add_profile(
        bar,
        hours=[interval(Weekday.FRIDAY, "18:00", "02:00")],
        slot_minutes=60,
        min_notice_minutes=0,
    )
    world.add_resource(bar, "Bancone", capacity=10)

    saturday = world.check_availability().run(
        AvailabilityQuery(business_id=bar.id, date=LocalDate("2026-10-10"))
    )

    assert saturday.is_open_on_date
    assert times(saturday) == ["00:00", "00:30", "01:00"]


def test_kolkata_half_hour_offset_and_new_york_dst_gap_day() -> None:
    world = OperationsWorld(datetime.fromisoformat("2026-03-01T00:00:00+00:00"))
    clinic = world.add_business(
        name="Kolkata Dental",
        country_code="IN",
        timezone="Asia/Kolkata",
        currency_code="INR",
        languages=("en", "hi"),
        owner_language="en",
    )
    world.add_profile(
        clinic,
        hours=every_day("09:00", "11:00"),
        slot_minutes=60,
        min_notice_minutes=0,
        resource_kind=ResourceKind.STAFF,
    )
    world.add_resource(clinic, "Dr. Sen", capacity=1, kind=ResourceKind.STAFF)
    diner = world.add_business(
        name="Night Owl Diner",
        country_code="US",
        timezone="America/New_York",
        currency_code="USD",
        languages=("en", "es"),
        owner_language="en",
    )
    world.add_profile(
        diner,
        hours=[interval(Weekday.SUNDAY, "00:00", "06:00")],
        slot_minutes=60,
        min_notice_minutes=0,
    )
    world.add_resource(diner, "Booth", capacity=4)

    kolkata = world.check_availability().run(
        AvailabilityQuery(business_id=clinic.id, date=LocalDate("2026-03-10"))
    )
    gap_day = world.check_availability().run(
        AvailabilityQuery(business_id=diner.id, date=LocalDate("2026-03-08"))
    )

    assert times(kolkata) == ["09:00", "09:30", "10:00"]
    assert "02:00" not in times(gap_day) and "02:30" not in times(gap_day)
    assert times(gap_day)[:4] == ["00:00", "00:30", "01:00", "01:30"]
