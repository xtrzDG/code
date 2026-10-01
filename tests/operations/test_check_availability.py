from datetime import datetime

import pytest

from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.operations.builders import OperationsWorld, every_day, interval


class RestaurantFixture:
    """Tbilisi restaurant open 12:00-23:00, 2 h slots, 60 min notice."""

    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business: BusinessDocument = self.world.add_business()
        self.world.add_profile(self.business)
        self.table_for_two: ResourceDocument = self.world.add_resource(
            self.business, "Table 2", capacity=2
        )
        self.table_for_four: ResourceDocument = self.world.add_resource(
            self.business, "Table 4", capacity=4
        )
        self.table_for_eight: ResourceDocument = self.world.add_resource(
            self.business, "Table 8", capacity=8
        )
        self.contact: ContactDocument = self.world.add_contact(self.business, "Giorgi")

    def query(
        self,
        day: str = "2026-10-05",
        time: str | None = None,
        party_size: int | None = None,
        is_sandbox: bool = False,
        resource_id: ResourceId | None = None,
        duration_minutes: int | None = None,
    ) -> AvailabilityResult:
        return self.world.check_availability().run(
            AvailabilityQuery(
                business_id=self.business.id,
                date=LocalDate(day),
                time=None if time is None else LocalTimeOfDay(time),
                party_size=None if party_size is None else PartySize(party_size),
                is_sandbox=is_sandbox,
                resource_id=resource_id,
                duration_minutes=(
                    None
                    if duration_minutes is None
                    else BookingDurationMinutes(duration_minutes)
                ),
            )
        )


def times(result: AvailabilityResult) -> list[str]:
    return [str(slot.time) for slot in result.slots]


def test_nearest_five_slots_around_requested_time_with_best_fit_table() -> None:
    restaurant = RestaurantFixture()

    result = restaurant.query(time="19:00", party_size=3)

    assert result.timezone == "Asia/Tbilisi"
    assert result.is_open_on_date
    assert times(result) == ["18:00", "18:30", "19:00", "19:30", "20:00"]
    assert {slot.resource_name for slot in result.slots} == {"Table 4"}
    assert all(slot.duration_minutes == 120 for slot in result.slots)
    assert all(slot.booking_unit is BookingUnit.TIME_SLOT for slot in result.slots)


def test_first_ten_slots_respect_the_minimum_notice() -> None:
    restaurant = RestaurantFixture()

    # Now is 12:00 in Tbilisi and one hour of notice is required.
    result = restaurant.query()

    assert times(result) == [
        "13:00",
        "13:30",
        "14:00",
        "14:30",
        "15:00",
        "15:30",
        "16:00",
        "16:30",
        "17:00",
        "17:30",
    ]


def test_last_slot_ends_at_closing_time() -> None:
    restaurant = RestaurantFixture()

    result = restaurant.query(day="2026-10-06", time="23:00")

    assert times(result)[-1] == "21:00"


def test_party_above_profile_maximum_is_refused() -> None:
    restaurant = RestaurantFixture()

    with pytest.raises(ValidationFailedError, match="12 guests"):
        restaurant.query(party_size=13)


def test_party_larger_than_every_table_gets_no_slots_but_open_day() -> None:
    restaurant = RestaurantFixture()

    result = restaurant.query(party_size=9)

    assert result.is_open_on_date
    assert result.slots == []


def test_taken_table_moves_the_offer_to_the_next_best_fit() -> None:
    restaurant = RestaurantFixture()
    restaurant.world.add_booking(
        restaurant.business,
        restaurant.table_for_four,
        restaurant.contact,
        "2026-10-05T19:00:00+04:00",
        "2026-10-05T21:00:00+04:00",
    )

    result = restaurant.query(time="19:00", party_size=3)
    by_time = {str(slot.time): str(slot.resource_name) for slot in result.slots}

    assert by_time["19:00"] == "Table 8"
    assert by_time["20:00"] == "Table 8"


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


def test_sandbox_bookings_never_block_real_customers() -> None:
    restaurant = RestaurantFixture()
    for table in (
        restaurant.table_for_two,
        restaurant.table_for_four,
        restaurant.table_for_eight,
    ):
        restaurant.world.add_booking(
            restaurant.business,
            table,
            restaurant.contact,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            is_sandbox=True,
        )

    real = restaurant.query(day="2026-10-06", time="19:00", party_size=2)
    sandbox = restaurant.query(
        day="2026-10-06", time="19:00", party_size=2, is_sandbox=True
    )

    assert "19:00" in times(real)
    assert "19:00" not in times(sandbox)
    assert "20:00" not in times(sandbox)


def test_sandbox_sees_real_bookings_and_cancelled_ones_are_free() -> None:
    restaurant = RestaurantFixture()
    restaurant.world.add_booking(
        restaurant.business,
        restaurant.table_for_eight,
        restaurant.contact,
        "2026-10-06T19:00:00+04:00",
        "2026-10-06T21:00:00+04:00",
    )
    restaurant.world.add_booking(
        restaurant.business,
        restaurant.table_for_eight,
        restaurant.contact,
        "2026-10-06T13:00:00+04:00",
        "2026-10-06T15:00:00+04:00",
        status=BookingStatus.CANCELLED,
    )

    sandbox = restaurant.query(
        day="2026-10-06", time="19:00", party_size=6, is_sandbox=True
    )
    real = restaurant.query(day="2026-10-06", time="13:00", party_size=6)

    assert "19:00" not in times(sandbox)
    assert "13:00" in times(real)


def test_resource_by_id_and_unknown_or_inactive_resources() -> None:
    restaurant = RestaurantFixture()
    inactive = restaurant.world.add_resource(
        restaurant.business, "Terrace", capacity=6, is_active=False
    )

    only_table_two = restaurant.query(
        time="19:00", resource_id=restaurant.table_for_two.id
    )

    assert {slot.resource_id for slot in only_table_two.slots} == {
        restaurant.table_for_two.id
    }
    with pytest.raises(NotFoundError):
        restaurant.query(resource_id=ResourceId())

    with pytest.raises(NotFoundError):
        restaurant.query(resource_id=inactive.id)


def test_unknown_business_is_not_found() -> None:
    world = OperationsWorld()

    with pytest.raises(NotFoundError):
        world.check_availability().run(
            AvailabilityQuery(business_id=BusinessId(), date=LocalDate("2026-10-05"))
        )


def test_requested_duration_overrides_the_profile_slot() -> None:
    restaurant = RestaurantFixture()

    result = restaurant.query(day="2026-10-06", time="22:00", duration_minutes=30)

    assert times(result)[-1] == "22:30"
    assert all(slot.duration_minutes == 30 for slot in result.slots)


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


class HotelFixture:
    """Rome hotel with two identical double rooms booked by the night."""

    def __init__(self) -> None:
        self.world = OperationsWorld(
            datetime.fromisoformat("2026-10-05T08:00:00+00:00")
        )
        self.business = self.world.add_business(
            name="Hotel Aurora",
            country_code="IT",
            timezone="Europe/Rome",
            currency_code="EUR",
            languages=("it", "en", "de"),
            owner_language="it",
        )
        self.world.add_profile(
            self.business,
            resource_kind=ResourceKind.ROOM,
            min_notice_minutes=0,
            niche_answers={"check_in_time": "15:00", "check_out_time": "10:00"},
        )
        self.double_rooms = self.world.add_resource(
            self.business,
            "Double room",
            capacity=2,
            unit_count=2,
            kind=ResourceKind.ROOM,
            booking_unit=BookingUnit.NIGHT,
        )
        self.contact = self.world.add_contact(self.business, "Marco")

    def query(self, day: str, nights: int, party_size: int = 2) -> AvailabilityResult:
        return self.world.check_availability().run(
            AvailabilityQuery(
                business_id=self.business.id,
                date=LocalDate(day),
                nights=NightCount(nights),
                party_size=PartySize(party_size),
            )
        )


def test_hotel_stays_count_units_per_night() -> None:
    hotel = HotelFixture()
    # One room taken for night 1, another room for night 3.
    hotel.world.add_booking(
        hotel.business,
        hotel.double_rooms,
        hotel.contact,
        "2026-10-12T15:00:00+02:00",
        "2026-10-13T10:00:00+02:00",
    )
    hotel.world.add_booking(
        hotel.business,
        hotel.double_rooms,
        hotel.contact,
        "2026-10-14T15:00:00+02:00",
        "2026-10-15T10:00:00+02:00",
    )

    result = hotel.query("2026-10-12", nights=3)

    assert len(result.slots) == 1
    stay = result.slots[0]
    assert stay.booking_unit is BookingUnit.NIGHT
    assert (stay.date, stay.time, stay.nights) == ("2026-10-12", "15:00", 3)

    hotel.world.add_booking(
        hotel.business,
        hotel.double_rooms,
        hotel.contact,
        "2026-10-13T15:00:00+02:00",
        "2026-10-15T10:00:00+02:00",
    )
    assert hotel.query("2026-10-12", nights=3).slots == []
    # Checking out on the 12th at 10:00 frees the room for a 15:00 check-in.
    assert hotel.query("2026-10-15", nights=1).slots != []


def test_hotel_closed_night_blocks_the_whole_stay() -> None:
    hotel = HotelFixture()
    hotel.world.add_exception(hotel.business, "2026-10-13")

    assert hotel.query("2026-10-12", nights=3).slots == []
    assert hotel.query("2026-10-14", nights=2).slots != []
    assert not hotel.query("2026-10-13", nights=1).is_open_on_date
    # The room does not seat three guests.
    assert hotel.query("2026-10-20", nights=1, party_size=3).slots == []
