"""The value model: what the assistant did and is worth, against the week before."""

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.value import AverageCheckSource, ValueBasis, ValuePeriod
from app.schemas.domain.value_settings import ValueSettingsDocument
from app.schemas.dto.value.value_model import ValueModel, ValueTotals
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    EstimatedRevenueMinor,
    StaffMinutesSaved,
)
from app.utilities.value.value_keys import value_settings_id_of
from tests.value.value_scene import ValueScene


def busy_week() -> ValueScene:
    """Last week (Sep 28 to Oct 4) and one booking the week before."""

    scene = ValueScene()
    lunch = scene.conversation("2026-09-28T13:00:00+04:00")
    for minute in ("01", "02", "03"):
        scene.message(lunch, f"2026-09-28T13:{minute}:00+04:00")
    scene.message(lunch, "2026-09-28T13:00:30+04:00", MessageAuthor.CUSTOMER)
    scene.message(lunch, "2026-09-28T13:02:30+04:00", MessageAuthor.CUSTOMER)
    scene.booking("2026-09-28T13:05:00+04:00", lunch)
    scene.booking("2026-09-28T13:06:00+04:00", lunch, BookingStatus.CANCELLED)
    scene.handoff(lunch, "2026-09-28T13:10:00+04:00")
    # 02:00 is outside the opening hours (12:00 to 23:00): after hours.
    night = scene.conversation("2026-09-29T02:00:00+04:00", ChannelKind.TELEGRAM)
    scene.message(night, "2026-09-29T02:01:00+04:00")
    scene.message(night, "2026-09-29T02:02:00+04:00")
    scene.booking("2026-09-29T02:05:00+04:00", night, BookingStatus.PENDING)
    scene.lead("2026-09-29T02:06:00+04:00")
    call = scene.conversation("2026-09-30T15:00:00+04:00", ChannelKind.PHONE)
    scene.booking("2026-09-30T15:04:00+04:00", call, BookingStatus.COMPLETED)
    # Flagged by the conversation engine (a holiday) though inside the hours.
    scene.conversation("2026-10-01T15:00:00+04:00", is_after_hours=True)
    test_chat = scene.conversation(
        "2026-10-01T15:00:00+04:00", ChannelKind.OWNER_TEST, is_sandbox=True
    )
    for minute in ("01", "02", "03", "04"):
        scene.message(test_chat, f"2026-10-01T15:{minute}:00+04:00")
    scene.booking("2026-10-01T15:05:00+04:00", test_chat, is_sandbox=True)
    # Staff added this one in the cabinet: a booking, not the assistant's.
    scene.booking("2026-10-02T12:30:00+04:00", None)
    before = scene.conversation("2026-09-22T13:00:00+04:00")
    scene.message(before, "2026-09-22T13:01:00+04:00")
    scene.booking("2026-09-22T13:05:00+04:00", before)
    return scene


def last_week(scene: ValueScene, user_id: UserId | None = None) -> ValueModel:
    return scene.world.business_value().run(
        BusinessValueQuery(
            user_id=user_id or scene.owner.id,
            business_id=scene.business.id,
            period=ValuePeriod.LAST_WEEK,
        )
    )


def test_the_week_counts_the_assistants_bookings_hours_and_minutes() -> None:
    model = last_week(busy_week())

    assert (model.date_from, model.date_to) == ("2026-09-28", "2026-10-04")
    assert (model.previous_date_from, model.previous_date_to) == (
        "2026-09-21",
        "2026-09-27",
    )
    assert model.current == ValueTotals(
        conversation_count=PeriodItemCount(4),
        after_hours_conversation_count=PeriodItemCount(2),
        customer_message_count=PeriodItemCount(2),
        assistant_reply_count=PeriodItemCount(5),
        call_count=PeriodItemCount(1),
        booking_count=PeriodItemCount(5),
        assistant_booking_count=PeriodItemCount(3),
        request_count=PeriodItemCount(1),
        handoff_count=PeriodItemCount(1),
        # 5 replies x 75 s + 1 call x 180 s = 555 s.
        staff_minutes_saved=StaffMinutesSaved(9),
        # 3 bookings x the typical check of a restaurant (40 EUR = 120 GEL).
        estimated_revenue_minor=EstimatedRevenueMinor(36_000),
    )
    assert model.previous.assistant_booking_count == 1
    assert model.previous.conversation_count == 1
    assert model.previous.staff_minutes_saved == 1
    assert model.previous.estimated_revenue_minor == 12_000


def test_the_estimate_explains_its_rates() -> None:
    model = last_week(busy_week())

    assert model.value_basis is ValueBasis.BOOKINGS
    assert model.average_check_source is AverageCheckSource.NICHE_DEFAULT
    assert model.average_check_minor == model.typical_check_minor == 12_000
    assert (model.seconds_per_reply, model.seconds_per_call) == (75, 180)
    assert (model.currency_code, model.timezone) == ("GEL", "Asia/Tbilisi")


def test_the_owners_average_check_replaces_the_typical_one() -> None:
    scene = busy_week()
    scene.world.value_settings_repo.save(
        ValueSettingsDocument(
            id=value_settings_id_of(scene.business.id),
            business_id=scene.business.id,
            average_check_minor=AverageCheckMinor(15_000),
        )
    )

    model = last_week(scene)

    assert model.average_check_source is AverageCheckSource.OWNER
    assert model.average_check_minor == 15_000
    assert model.typical_check_minor == 12_000
    assert model.current.estimated_revenue_minor == 45_000


def test_staff_see_the_counts_but_no_money() -> None:
    scene = busy_week()

    model = last_week(scene, scene.staff_id)

    assert model.current.assistant_booking_count == 3
    assert model.current.estimated_revenue_minor is None
    assert model.previous.estimated_revenue_minor is None
    assert model.average_check_minor is None and model.typical_check_minor is None
    assert model.average_check_source is AverageCheckSource.NONE


def test_a_quiet_period_counts_zero_everywhere() -> None:
    scene = ValueScene()

    model = last_week(scene)

    assert model.current.conversation_count == 0
    assert model.current.estimated_revenue_minor == 0
    assert model.current.staff_minutes_saved == 0
