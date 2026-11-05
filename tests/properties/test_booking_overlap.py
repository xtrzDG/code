"""
Booking units without double booking (SDLC-07): the peak overlap a new
booking is checked against is the true largest number of bookings at one
instant, and taking requests one by one with `has_free_unit` never puts
more bookings on a resource at once than it has units; touching bookings
(one ends when the next starts) share a unit.
"""

from hypothesis import given
from hypothesis import strategies as st

from app.utilities.scheduling.overlap import (
    BusyRange,
    has_free_unit,
    max_concurrent_overlap,
)

DAY_START: int = 1_791_000_000
SLOT: int = 15 * 60


@st.composite
def ranges(draw: st.DrawFn) -> BusyRange:
    """A booking on the quarter-hour grid of one day, 15 minutes to 4 hours."""

    start = DAY_START + draw(st.integers(0, 95)) * SLOT
    return BusyRange(start, start + draw(st.integers(1, 16)) * SLOT)


def brute_force_peak(busy: list[BusyRange], starts_at: int, ends_at: int) -> int:
    """The most bookings that hold one instant of [starts_at, ends_at)."""

    instants = {starts_at} | {
        moment
        for booking in busy
        for moment in (booking.starts_at, booking.ends_at)
        if starts_at <= moment < ends_at
    }
    return max(
        sum(1 for booking in busy if booking.starts_at <= moment < booking.ends_at)
        for moment in instants
    )


@given(st.lists(ranges(), max_size=25), ranges())
def test_the_peak_overlap_is_the_true_peak(
    busy: list[BusyRange], window: BusyRange
) -> None:
    assert max_concurrent_overlap(busy, window.starts_at, window.ends_at) == (
        brute_force_peak(busy, window.starts_at, window.ends_at)
    )


@given(st.lists(ranges(), max_size=40), st.integers(1, 4))
def test_taking_requests_one_by_one_never_double_books(
    requests: list[BusyRange], units: int
) -> None:
    taken: list[BusyRange] = []
    for request in requests:
        if has_free_unit(taken, request.starts_at, request.ends_at, units):
            taken.append(request)

    whole_day = (DAY_START, DAY_START + 200 * SLOT)
    assert brute_force_peak(taken, *whole_day) <= units
    for request in requests:
        if request not in taken:
            assert brute_force_peak(taken, request.starts_at, request.ends_at) >= units


@given(st.lists(ranges(), min_size=1, max_size=20))
def test_one_unit_never_holds_two_bookings_at_once(requests: list[BusyRange]) -> None:
    taken: list[BusyRange] = []
    for request in requests:
        if has_free_unit(taken, request.starts_at, request.ends_at, 1):
            taken.append(request)

    ordered = sorted(taken)
    assert all(
        earlier.ends_at <= later.starts_at
        for earlier, later in zip(ordered, ordered[1:], strict=False)
    )
    assert taken[0] == requests[0]


@given(ranges(), st.integers(1, 16))
def test_a_booking_that_starts_when_another_ends_shares_its_unit(
    first: BusyRange, length: int
) -> None:
    following = BusyRange(first.ends_at, first.ends_at + length * SLOT)

    assert has_free_unit([first], following.starts_at, following.ends_at, 1)
    assert has_free_unit([following], first.starts_at, first.ends_at, 1)
