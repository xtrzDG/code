"""
Dragging a booking on the calendar: it lands on the place it was dropped
on (or nowhere), only from the start the calendar showed, and Undo is the
same move back.
"""

import pytest

from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from tests.bookings_calendar.grid_world import GridWorld, GuestHouseGrid


def test_a_booking_dragged_to_another_table_moves_there_and_back() -> None:
    world = GridWorld()
    booking = world.book(world.window, "2026-10-06T19:00", "2026-10-06T21:00")

    moved = world.move(
        booking, "2026-10-06", "20:00", world.terrace.id, ("2026-10-06", "19:00")
    )

    assert (moved.booking.resource_name, moved.booking.time) == ("Terrace", "20:00")
    assert moved.booking.end_time == "22:00"
    assert "20:00" in moved.confirmation_text

    undone = world.move(
        booking, "2026-10-06", "19:00", world.window.id, ("2026-10-06", "20:00")
    )
    assert (undone.booking.resource_name, undone.booking.time) == (
        "Window table",
        "19:00",
    )


def test_a_drop_on_a_taken_place_does_not_land_elsewhere() -> None:
    world = GridWorld()
    world.book(world.window, "2026-10-06T20:00", "2026-10-06T22:00")
    booking = world.book(world.window, "2026-10-06T13:00", "2026-10-06T15:00")
    other = world.world.add_resource(world.business, "Other table", capacity=2)

    with pytest.raises(ConflictError, match="already booked"):
        world.move(booking, "2026-10-06", "20:00", world.window.id)

    # Without a place, the move takes another free table of the same kind.
    moved = world.move(booking, "2026-10-06", "20:00")
    assert moved.booking.resource_id == other.id


def test_a_move_from_a_start_the_calendar_no_longer_shows_is_refused() -> None:
    world = GridWorld()
    booking = world.book(world.window, "2026-10-06T19:00", "2026-10-06T21:00")
    world.move(booking, "2026-10-06", "17:00")

    with pytest.raises(ConflictError) as refused:
        world.move(
            booking, "2026-10-06", "20:00", world.terrace.id, ("2026-10-06", "19:00")
        )

    assert [reason.code for reason in refused.value.reasons] == ["booking_changed"]
    with pytest.raises(ConflictError):
        world.move(booking, "2026-10-07", "20:00", None, ("2026-10-05", None))
    moved = world.move(booking, "2026-10-07", "20:00", None, ("2026-10-06", None))
    assert moved.booking.date == "2026-10-07"


def test_a_drop_target_is_checked_like_a_new_place() -> None:
    world = GridWorld()
    booking = world.book(
        world.terrace, "2026-10-06T13:00", "2026-10-06T14:00", party_size=4
    )
    retired = world.world.add_resource(world.business, "Retired", is_active=False)

    with pytest.raises(ValidationFailedError, match="seats at most 2"):
        world.move(booking, "2026-10-06", "15:00", world.window.id)
    with pytest.raises(NotFoundError):
        world.move(booking, "2026-10-06", "15:00", retired.id)
    with pytest.raises(ValidationFailedError, match="closed"):
        world.move(booking, "2026-10-06", "13:00", world.hall.id)


def test_a_table_booking_cannot_be_dropped_on_a_room() -> None:
    house = GuestHouseGrid()
    booking = house.book(house.window, "2026-10-06T19:00", "2026-10-06T21:00")

    with pytest.raises(ValidationFailedError, match="booked by nights"):
        house.move(booking, "2026-10-06", "19:00", house.deluxe.id)


def test_a_stay_dragged_to_another_room_keeps_its_nights() -> None:
    house = GuestHouseGrid()
    stay = house.book(house.deluxe, "2026-10-06T14:00", "2026-10-08T12:00")

    moved = house.move(
        stay, "2026-10-07", None, house.standard.id, ("2026-10-06", None)
    )

    assert (moved.booking.resource_name, moved.booking.date) == (
        "Standard",
        "2026-10-07",
    )
    assert moved.booking.end_date == "2026-10-09"
