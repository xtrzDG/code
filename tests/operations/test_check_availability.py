"""Restaurant availability: slots, notice, party sizes, tables, sandbox, resources."""

import pytest

from app.schemas.constants.bookings import BookingStatus, BookingUnit
from app.schemas.dto.bookings import AvailabilityQuery
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.operations.availability_fixtures import RestaurantFixture, times
from tests.operations.operations_world import OperationsWorld


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
