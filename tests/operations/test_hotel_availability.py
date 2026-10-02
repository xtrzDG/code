"""Hotel availability: rooms counted per night and closed nights."""

from datetime import datetime

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.typings.bookings.constrained_integers import (
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from tests.operations.operations_world import OperationsWorld


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
