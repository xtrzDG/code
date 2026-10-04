"""Room types for N nights: nightly rates by season, quotes, stays and values."""

from datetime import date

import pytest

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.bookings.stay_quotes import is_in_season, quote_stay
from tests.bookings.hotel_fixture import HOLIDAYS, SUMMER, GuestHouse, season
from tests.bookings.salon_fixture import reason_code

GEL = CurrencyCode("GEL")


def nightly(house: GuestHouse, check_in: date, nights: int) -> list[int]:
    quote = quote_stay(house.deluxe, check_in, nights, GEL)
    assert quote is not None
    return [int(night.nightly_rate_minor) for night in quote.night_prices]


def test_a_stay_across_two_seasons_is_priced_night_by_night() -> None:
    house = GuestHouse()

    quote = quote_stay(house.deluxe, date(2027, 8, 30), 3, GEL)

    assert quote is not None
    assert (quote.check_in, quote.check_out, quote.nights) == (
        "2027-08-30",
        "2027-09-02",
        3,
    )
    # August 30 and 31 are summer nights, September 1 is not.
    assert [str(night.date) for night in quote.night_prices] == [
        "2027-08-30",
        "2027-08-31",
        "2027-09-01",
    ]
    assert nightly(house, date(2027, 8, 30), 3) == [30000, 30000, 20000]
    assert [night.season_name for night in quote.night_prices] == [
        "Summer",
        "Summer",
        None,
    ]
    assert (quote.total_minor, quote.currency_code) == (80000, "GEL")
    assert (quote.item_id, quote.item_title) == (house.deluxe.id, "Deluxe room")


def test_a_season_over_new_year_wraps_around_the_year() -> None:
    house = GuestHouse()

    assert nightly(house, date(2026, 12, 30), 3) == [35000, 35000, 35000]
    assert nightly(house, date(2027, 1, 9), 3) == [35000, 35000, 20000]
    holidays = season(*HOLIDAYS)
    assert is_in_season(date(2026, 12, 20), holidays)
    assert is_in_season(date(2027, 1, 10), holidays)
    assert not is_in_season(date(2026, 12, 19), holidays)
    assert not is_in_season(date(2027, 1, 11), holidays)
    summer = season(*SUMMER)
    assert is_in_season(date(2027, 7, 1), summer)
    assert not is_in_season(date(2027, 9, 1), summer)


def test_without_a_base_rate_a_night_outside_every_season_has_no_price() -> None:
    house = GuestHouse()
    seasonal_only = house.room_type("Garden suite", None, [season(*SUMMER)])

    assert quote_stay(seasonal_only, date(2027, 8, 1), 2, GEL) is not None
    assert quote_stay(seasonal_only, date(2027, 8, 31), 2, GEL) is None


def test_get_price_quotes_the_deluxe_room_for_three_nights_in_august() -> None:
    house = GuestHouse()

    result = house.price("deluxe room", check_in="2027-08-10", nights=3)

    assert str(result.matches[0].title) == "Deluxe room"
    assert len(result.matches[0].seasonal_rates) == 2
    totals = {str(quote.item_title): quote.total_minor for quote in result.stay_quotes}
    # Every matching room type is quoted, best match first.
    assert totals["Deluxe room"] == 90000
    assert result.stay_quotes[0].item_id == house.deluxe.id
    assert house.price("deluxe room").stay_quotes == []


def test_availability_of_a_room_type_offers_its_rooms_with_the_stay_price() -> None:
    house = GuestHouse()

    result = house.query("2027-08-10", 3, service="Deluxe")

    assert {str(slot.resource_name) for slot in result.slots} == {
        "Room 101",
        "Room 102",
    }
    for slot in result.slots:
        assert slot.stay_quote is not None
        assert (slot.stay_quote.total_minor, slot.nights) == (90000, 3)
    assert result.service is not None and result.service.title == "Deluxe room"


def test_rooms_without_a_named_type_are_quoted_by_their_own_type() -> None:
    house = GuestHouse()

    result = house.query("2027-08-10", 2)

    totals = {
        str(slot.resource_name): None
        if slot.stay_quote is None
        else int(slot.stay_quote.total_minor)
        for slot in result.slots
    }
    assert totals == {"Room 101": 60000, "Room 102": 60000, "Room 201": 24000}
    assert [str(offer.title) for offer in result.services] == [
        "Deluxe room",
        "Standard room",
    ]


def test_booking_the_deluxe_room_for_three_nights_carries_the_stay_value() -> None:
    house = GuestHouse()

    result = house.book("2027-08-30", 3)

    view = result.booking
    assert view.resource_name in {"Room 101", "Room 102"}
    assert (view.date, view.end_date) == ("2027-08-30", "2027-09-02")
    assert (view.time, view.end_time) == ("14:00", "12:00")
    assert (view.service_item_id, view.service_title) == (
        house.deluxe.id,
        "Deluxe room",
    )
    assert (view.value_minor, view.currency_code) == (80000, "GEL")
    stored = house.world.bookings_of(house.business.id)[0]
    assert (stored.value_minor, stored.currency_code) == (80000, "GEL")
    # Room types keep no buffer: the next guest checks in the same day.
    assert stored.buffer_minutes is None


def test_a_room_booked_by_id_is_valued_by_its_room_type() -> None:
    house = GuestHouse()

    result = house.book("2027-08-10", 2, service=None, resource_id=house.room_201.id)

    assert result.booking.service_item_id == house.standard.id
    assert result.booking.value_minor == 24000


def test_a_room_of_another_type_is_refused_for_the_named_type() -> None:
    house = GuestHouse()

    with pytest.raises(ValidationFailedError) as error:
        house.book("2027-08-10", 2, resource_id=house.room_201.id)

    assert reason_code(error.value) == BookingRefusalCode.NOT_PERFORMED


def test_the_last_deluxe_room_taken_leaves_none_for_the_same_nights() -> None:
    house = GuestHouse()
    house.book("2027-08-10", 3)
    house.book("2027-08-11", 1)

    assert house.query("2027-08-11", 1, service="deluxe").slots == []
    assert house.query("2027-08-13", 1, service="deluxe").slots != []


def test_rescheduling_a_stay_prices_its_new_nights() -> None:
    house = GuestHouse()
    stay = house.book("2027-08-30", 3)

    moved = house.world.reschedule_booking().run(
        house.reschedule_command(stay.booking.id, "2027-09-10")
    )

    # Three September nights at the base rate.
    assert moved.booking.value_minor == 60000
    assert moved.booking.date == "2027-09-10"
