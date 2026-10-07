"""
The bookings calendar in one call: places as columns with their own
hours, how full each is, the bookings of the window (cancelled and test
ones left out), and the audit of who looked at customers' names.
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.compliance import AuditAction
from app.schemas.dto.booking_grid import BookingGridPlaceDay, GridOpenRange
from app.schemas.exceptions.application_errors import ValidationFailedError
from tests.bookings_calendar.grid_world import GridWorld
from tests.operations.builders import interval

EVENING = (18 * 60, 23 * 60)


def ranges(
    place_day: BookingGridPlaceDay | list[GridOpenRange],
) -> list[tuple[int, int]]:
    found = place_day if isinstance(place_day, list) else place_day.open_ranges
    return [(int(opening.opens_at), int(opening.closes_at)) for opening in found]


def test_places_are_columns_with_their_hours_and_load() -> None:
    world = GridWorld()
    world.book(world.window, "2026-10-06T19:00", "2026-10-06T21:00")
    world.book(world.terrace, "2026-10-06T13:00", "2026-10-06T14:00")
    world.book(world.terrace, "2026-10-06T13:30", "2026-10-06T15:00", party_size=4)
    world.book(
        world.window,
        "2026-10-06T13:00",
        "2026-10-06T15:00",
        status=BookingStatus.CANCELLED,
    )
    world.book(world.hall, "2026-10-06T19:00", "2026-10-06T22:00", is_sandbox=True)

    grid = world.grid()

    assert [place.name for place in grid.places] == ["Window table", "Terrace", "Hall"]
    assert (grid.date_from, grid.date_to, grid.timezone) == (
        "2026-10-06",
        "2026-10-06",
        "Asia/Tbilisi",
    )
    day = grid.days[0]
    window, terrace, hall = day.places
    assert ranges(day.business_ranges) == [(12 * 60, 23 * 60)]
    assert ranges(window) == [(12 * 60, 23 * 60)]
    assert (window.open_unit_minutes, window.booked_unit_minutes) == (660, 120)
    # Three terrace tables: 3 x 11 hours open, an hour and an hour and a half taken.
    assert (terrace.open_unit_minutes, terrace.booked_unit_minutes) == (1980, 150)
    assert terrace.booking_count == 2
    assert ranges(hall) == [EVENING]
    assert (hall.open_unit_minutes, hall.booking_count) == (300, 0)
    assert window.open_units is None and window.booked_units is None
    assert sorted(f"{item.resource_name} {item.time}" for item in grid.bookings) == [
        "Terrace 13:00",
        "Terrace 13:30",
        "Window table 19:00",
    ]
    assert not grid.is_truncated

    with_tests = world.grid(include_sandbox=True)
    assert with_tests.days[0].places[2].booking_count == 1
    assert len(with_tests.bookings) == 4


def test_a_view_with_names_is_audited_and_the_counts_alone_are_not() -> None:
    world = GridWorld()
    world.book(world.window, "2026-10-06T19:00", "2026-10-06T21:00")

    counts = world.grid(include_bookings=False)
    assert counts.bookings == []
    assert counts.days[0].places[0].booking_count == 1
    assert world.world.audit_repo.list_by_business(world.business.id) == []

    world.grid()
    entries = world.world.audit_repo.list_by_business(world.business.id)
    assert [
        (entry.action, entry.entity, entry.actor_id, entry.ip_address)
        for entry in entries
    ] == [(AuditAction.VIEW, "booking", world.staff_id, "203.0.113.7")]


def test_bookings_carried_over_midnight_show_on_the_next_day() -> None:
    world = GridWorld(hours=("18:00", "02:00"))
    carried = world.book(world.window, "2026-10-05T23:00", "2026-10-06T01:30")
    # It ends exactly when the day begins: nothing of it is on the day.
    world.book(world.terrace, "2026-10-05T22:00", "2026-10-06T00:00")

    grid = world.grid()

    assert [item.id for item in grid.bookings] == [carried.id]
    window, terrace, hall = grid.days[0].places
    assert ranges(grid.days[0].business_ranges) == [(0, 120), (18 * 60, 24 * 60)]
    assert ranges(window) == [(0, 120), (18 * 60, 24 * 60)]
    assert (window.booking_count, window.booked_unit_minutes) == (1, 90)
    assert terrace.booking_count == 0
    # The hall keeps its own evening hours on overnight business days.
    assert ranges(hall) == [EVENING]


def test_holidays_and_special_hours_shape_the_day() -> None:
    world = GridWorld()
    world.world.add_exception(world.business, "2026-10-07")
    world.world.add_exception(
        world.business,
        "2026-10-08",
        resource=world.terrace,
        special_hours=[interval(Weekday.THURSDAY, "15:00", "17:00")],
    )

    grid = world.grid(date="2026-10-06", days=3)

    assert [day.date for day in grid.days] == ["2026-10-06", "2026-10-07", "2026-10-08"]
    closed = grid.days[1]
    assert closed.business_ranges == []
    assert [(place.is_open, place.open_unit_minutes) for place in closed.places] == [
        (False, 0),
        (False, 0),
        (False, 0),
    ]
    terrace = grid.days[2].places[1]
    assert ranges(terrace) == [(15 * 60, 17 * 60)]
    assert terrace.open_unit_minutes == 3 * 120


def test_an_inactive_place_shows_only_while_it_has_bookings() -> None:
    world = GridWorld()
    old = world.world.add_resource(world.business, "Old booth", is_active=False)
    world.world.add_resource(world.business, "Gone booth", is_active=False)
    world.book(old, "2026-10-06T19:00", "2026-10-06T20:00")

    grid = world.grid()

    assert [place.name for place in grid.places] == [
        "Window table",
        "Terrace",
        "Hall",
        "Old booth",
    ]
    assert grid.places[3].is_active is False


def test_a_window_past_the_last_date_is_refused() -> None:
    world = GridWorld()

    with pytest.raises(ValidationFailedError, match="last date"):
        world.grid(date="2199-12-31", days=2)
