"""
The nights grid of a guest house (rooms by nights) and how the window's
bookings are read: a stay that began before the window, keyset pages and
the ceiling that says the calendar is incomplete.
"""

import pytest

from app.use_cases.bookings.calendar import grid_window
from tests.bookings_calendar.grid_world import GridWorld, GuestHouseGrid


def nights(grid_world: GuestHouseGrid, date: str, days: int) -> dict[str, list[str]]:
    """Per room: "taken/for sale" for each night of the window."""

    grid = grid_world.grid(date=date, days=days)
    names = {place.id: place.name for place in grid.places}
    table: dict[str, list[str]] = {}
    for day in grid.days:
        for place_day in day.places:
            if place_day.open_units is None:
                continue

            table.setdefault(str(names[place_day.resource_id]), []).append(
                f"{int(place_day.booked_units or 0)}/{int(place_day.open_units)}"
            )

    return table


def test_rooms_count_the_nights_taken_and_for_sale() -> None:
    house = GuestHouseGrid()
    house.book(house.deluxe, "2026-10-06T14:00", "2026-10-08T12:00")
    house.book(house.deluxe, "2026-10-07T14:00", "2026-10-09T12:00")
    # A week's stay that began before the window still holds its room.
    house.book(house.standard, "2026-09-30T14:00", "2026-10-07T12:00")
    house.world.add_exception(house.business, "2026-10-08", resource=house.standard)

    assert nights(house, "2026-10-06", 4) == {
        "Deluxe": ["1/2", "2/2", "1/2", "0/2"],
        "Standard": ["1/1", "0/1", "0/0", "0/1"],
    }
    grid = house.grid(date="2026-10-06", days=4)
    assert len(grid.bookings) == 3
    standard_day = grid.days[2].places[4]
    assert (standard_day.is_open, standard_day.open_ranges) == (False, [])
    assert standard_day.open_unit_minutes is None


def test_the_window_is_read_in_keyset_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grid_window, "PAGE_SIZE", 2)
    world = GridWorld()
    for hour in range(13, 18):
        world.book(world.terrace, f"2026-10-06T{hour}:00", f"2026-10-06T{hour}:30")
    world.book(world.window, "2026-10-05T23:00", "2026-10-06T00:30")

    grid = world.grid()

    assert [item.time for item in grid.bookings] == [
        "23:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
    ]
    assert not grid.is_truncated


def test_a_window_over_the_ceiling_says_it_is_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(grid_window, "PAGE_SIZE", 2)
    monkeypatch.setattr(grid_window, "READ_CEILING", 3)
    world = GridWorld()
    for hour in range(13, 18):
        world.book(world.terrace, f"2026-10-06T{hour}:00", f"2026-10-06T{hour}:30")

    grid = world.grid()

    assert grid.is_truncated
    assert [item.time for item in grid.bookings] == ["13:00", "14:00", "15:00"]

    carried_over = GridWorld()
    for day in range(1, 5):
        carried_over.book(
            carried_over.terrace, f"2026-10-0{day}T20:00", "2026-10-06T20:30"
        )
    assert carried_over.grid().is_truncated
