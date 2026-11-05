"""
Reports → Deposits compares no-shows before and after: every finished
booking in the same number of days before the owner first turned deposits
on, against those since; each honest below the sample it trusts, and
absent while deposits were never on.
"""

from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.contacts import ContactDocument
from tests.deposits.deposit_owner_actions import switch_deposits
from tests.deposits.deposit_store import at
from tests.deposits.deposit_world import DepositWorld

DAY_MINUTES: int = 24 * 60


def finished_bookings(
    world: DepositWorld, guest: ContactDocument, day: str, count: int, no_shows: int
) -> None:
    """`count` visits of one day, the first `no_shows` of them missed."""

    for index in range(count):
        world.add_booking(
            world.business,
            world.table_for_eight,
            guest,
            at("12:00", day),
            at("14:00", day),
            status=BookingStatus.NO_SHOW
            if index < no_shows
            else BookingStatus.COMPLETED,
        )


def test_no_shows_before_and_since_deposits_are_compared() -> None:
    world = DepositWorld()
    world.take_deposits(is_enabled=False)
    nino = world.guest("Nino", "ru")
    # Two weeks before deposits: a quarter of the guests did not come.
    finished_bookings(world, nino, "2026-09-20", count=20, no_shows=5)
    switch_deposits(world, is_enabled=True)
    world.pass_minutes(20 * DAY_MINUTES)
    finished_bookings(world, nino, "2026-10-10", count=20, no_shows=1)

    report = world.report(days=30)

    assert report.enabled_at is not None
    assert report.before_deposits is not None and report.since_deposits is not None
    assert int(report.before_deposits.finished_count) == 20
    assert int(report.before_deposits.no_show_percent or 0) == 25
    assert int(report.since_deposits.finished_count) == 20
    assert int(report.since_deposits.no_show_percent or 0) == 5


def test_a_small_group_before_deposits_says_not_enough_data() -> None:
    world = DepositWorld()
    world.take_deposits(is_enabled=False)
    nino = world.guest("Nino", "ru")
    finished_bookings(world, nino, "2026-09-20", count=19, no_shows=10)
    switch_deposits(world, is_enabled=True)

    report = world.report(days=30)

    assert report.before_deposits is not None
    assert report.before_deposits.has_enough_data is False
    assert report.before_deposits.no_show_percent is None


def test_no_comparison_while_deposits_were_never_on() -> None:
    world = DepositWorld()
    world.take_deposits(is_enabled=False)

    report = world.report(days=30)

    assert report.enabled_at is None
    assert report.before_deposits is None and report.since_deposits is None
