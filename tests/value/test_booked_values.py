"""The value model counts the assistant's bookings at their own values."""

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.value import RevenueSource, ValueBasis
from app.schemas.dto.value.value_model import ValueModel
from app.schemas.typings.value.constrained_integers import AverageCheckMinor
from app.use_cases.insights.value.value_money import BookedMoney, estimate_money
from tests.value.test_value_model import last_week
from tests.value.value_scene import ValueScene


def scene_with_values(with_unvalued: bool) -> ValueScene:
    """
    Last week (Sep 28 to Oct 4): a haircut (45 GEL) and a stay (800 GEL)
    booked by the assistant, and optionally one booking without a value.
    """

    scene = ValueScene()
    lunch = scene.conversation("2026-09-28T13:00:00+04:00")
    scene.booking("2026-09-28T13:05:00+04:00", lunch, value=(4_500, "GEL"))
    night = scene.conversation("2026-09-29T02:00:00+04:00")
    scene.booking(
        "2026-09-29T02:05:00+04:00", night, BookingStatus.PENDING, value=(80_000, "GEL")
    )
    # Cancelled: its value does not count.
    scene.booking(
        "2026-09-29T02:06:00+04:00",
        night,
        BookingStatus.CANCELLED,
        value=(7_000, "GEL"),
    )
    # Staff entered this one: a booking, not the assistant's.
    scene.booking("2026-09-30T12:30:00+04:00", None, value=(5_000, "GEL"))
    if with_unvalued:
        call = scene.conversation("2026-09-30T15:00:00+04:00")
        scene.booking("2026-09-30T15:04:00+04:00", call, BookingStatus.COMPLETED)

    return scene


def test_every_booking_with_a_value_counts_at_its_value() -> None:
    model: ValueModel = last_week(scene_with_values(with_unvalued=False))

    assert model.current.assistant_booking_count == 2
    assert model.current.valued_booking_count == 2
    assert model.current.booked_value_minor == 84_500
    assert model.current.estimated_revenue_minor == 84_500
    assert model.current.revenue_source is RevenueSource.BOOKED_VALUES


def test_bookings_without_a_value_count_at_the_average_check() -> None:
    model: ValueModel = last_week(scene_with_values(with_unvalued=True))

    assert model.current.assistant_booking_count == 3
    assert model.current.valued_booking_count == 2
    assert model.current.booked_value_minor == 84_500
    # 84.5 GEL + 800 GEL booked, and one booking at the typical 120 GEL.
    assert model.current.estimated_revenue_minor == 96_500
    assert model.current.revenue_source is RevenueSource.MIXED


def test_a_value_in_another_currency_counts_as_no_value() -> None:
    scene = ValueScene()
    chat = scene.conversation("2026-09-28T13:00:00+04:00")
    scene.booking("2026-09-28T13:05:00+04:00", chat, value=(4_500, "USD"))

    model = last_week(scene)

    assert model.current.valued_booking_count == 0
    assert model.current.booked_value_minor is None
    assert model.current.estimated_revenue_minor == 12_000
    assert model.current.revenue_source is RevenueSource.AVERAGE_CHECK


def test_staff_see_how_many_bookings_carry_a_value_but_no_money() -> None:
    scene = scene_with_values(with_unvalued=True)

    model = last_week(scene, scene.staff_id)

    assert model.current.valued_booking_count == 2
    assert model.current.booked_value_minor is None
    assert model.current.revenue_source is None
    assert model.current.estimated_revenue_minor is None


def test_the_money_estimate_rules() -> None:
    booked = BookedMoney(count=2, value_minor=10_000)
    check = AverageCheckMinor(3_000)

    mixed = estimate_money(ValueBasis.BOOKINGS, 5, booked, check)
    assert (mixed.estimated_revenue_minor, mixed.revenue_source) == (
        19_000,
        RevenueSource.MIXED,
    )
    unknown_check = estimate_money(ValueBasis.BOOKINGS, 5, booked, None)
    assert (unknown_check.estimated_revenue_minor, unknown_check.revenue_source) == (
        10_000,
        RevenueSource.BOOKED_VALUES,
    )
    requests = estimate_money(ValueBasis.REQUESTS, 4, booked, check)
    assert (requests.estimated_revenue_minor, requests.booked_value_minor) == (
        12_000,
        None,
    )
    nothing = estimate_money(ValueBasis.REQUESTS, 4, BookedMoney(0, 0), None)
    assert (nothing.estimated_revenue_minor, nothing.revenue_source) == (None, None)
