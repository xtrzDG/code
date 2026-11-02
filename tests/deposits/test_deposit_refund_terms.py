"""
Every deposit line and reminder tells the customer the refund terms before
they pay (Codice del consumo art. 49), in their language: a booking names
the last moment a cancellation still gets the deposit back (the moment
settling applies) or says a deposit asked past it is not refunded; a
banquet request names the cutoff in hours before the event.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.deposits.constrained_integers import DepositRefundCutoffHours
from app.utilities.deposits.deposit_line_texts import (
    DEPOSIT_BANQUET_LINE,
    DEPOSIT_BOOKING_LINE,
)
from app.utilities.deposits.deposit_refund_terms_texts import (
    DEPOSIT_NOT_REFUNDABLE,
    DEPOSIT_REFUND_ANY_TIME_BEFORE_EVENT,
    DEPOSIT_REFUND_BEFORE_EVENT,
    DEPOSIT_REFUND_UNTIL,
)
from app.utilities.deposits.deposit_reminder_texts import (
    DEPOSIT_BANQUET_REMINDER,
    DEPOSIT_BOOKING_REMINDER,
)
from app.utilities.deposits.deposit_settlement import refund_deadline, settled_status
from tests.deposits.deposit_world import DepositWorld
from tests.deposits.test_banquet_deposits import banquet_request, banquet_world

TERMS_TEXTS: tuple[LocalizedText, ...] = (
    DEPOSIT_REFUND_UNTIL,
    DEPOSIT_NOT_REFUNDABLE,
    DEPOSIT_REFUND_BEFORE_EVENT,
    DEPOSIT_REFUND_ANY_TIME_BEFORE_EVENT,
)
TODAY: str = "2026-10-05"
MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000


def line_of(world: DepositWorld, language: str, day: str, time: str = "19:00") -> str:
    guest = world.guest("Giulia", language)
    chat = world.telegram_conversation(guest)
    world.big_table_booking(guest, chat, time=time, day=day)
    receipt = world.ask_deposit(guest, chat)
    assert receipt.issued is not None
    return str(receipt.issued.line)


def test_the_line_names_the_last_moment_of_a_free_cancellation_in_italian() -> None:
    world = DepositWorld()
    world.take_deposits(refund_cutoff_hours=24)

    line = line_of(world, "it", day="2026-10-07")

    # The visit is on 7 October at 19:00: free cancellation until the 6th.
    terms = line.splitlines()[-1]
    assert terms.startswith("Se annulla entro ")
    assert "6 ott" in terms and "19:00" in terms
    assert "viene trattenuto" in terms


def test_a_cutoff_later_today_names_the_time_alone_in_english() -> None:
    world = DepositWorld()
    world.take_deposits(refund_cutoff_hours=2)

    line = line_of(world, "en", day=TODAY, time="19:00")

    assert line.splitlines()[-1] == (
        "Cancel by 17:00 and the deposit is refunded; after that, or if you "
        "do not come, it is kept."
    )


def test_a_deposit_asked_past_the_cutoff_says_it_is_not_refunded() -> None:
    world = DepositWorld()
    world.take_deposits(refund_cutoff_hours=24)

    line = line_of(world, "en", day=TODAY, time="19:00")

    assert line.splitlines()[-1] == (
        "Once paid, the deposit is not refunded if you cancel or do not come."
    )


@pytest.mark.parametrize(
    ("cutoff", "language", "expected"),
    [
        (24, "en", "If you cancel at least 24 hr before the event"),
        (48, "it", "Se annulla almeno 48 h prima dell'evento"),
        (0, "it", "Se annulla prima dell'evento"),
    ],
)
def test_a_banquet_line_names_the_cutoff_in_hours(
    cutoff: int, language: str, expected: str
) -> None:
    world = banquet_world()
    settings = world.deposit_settings_repo.get_by_business(world.business.id)
    assert settings is not None
    settings.refund_cutoff_hours = DepositRefundCutoffHours(cutoff)
    world.deposit_settings_repo.save(settings)
    guest = world.guest("Giulia", language)
    chat = world.telegram_conversation(guest)
    banquet_request(world, guest, chat)

    receipt = world.ask_deposit(guest, chat)

    assert receipt.issued is not None
    assert str(receipt.issued.line).splitlines()[-1].startswith(expected)


def test_the_reminder_repeats_the_terms() -> None:
    world = DepositWorld()
    world.take_deposits(hold_minutes=60, refund_cutoff_hours=24)
    line_of(world, "en", day="2026-10-07")

    world.pass_minutes(30)
    world.sweep()

    reminders = [text for text in world.outbox_texts() if "a reminder" in text]
    assert len(reminders) == 1
    assert reminders[0].splitlines()[-1].startswith("Cancel by ")
    assert "19:00" in reminders[0].splitlines()[-1]


def test_the_stated_moment_is_the_one_settling_applies() -> None:
    starts_at = BookingStartsAtUnixSeconds(1_760_000_000)
    cutoff = DepositRefundCutoffHours(24)
    deadline = refund_deadline(starts_at, cutoff)

    on_time = settled_status(BookingStatus.CANCELLED, starts_at, deadline, cutoff)
    late = settled_status(
        BookingStatus.CANCELLED,
        starts_at,
        Microseconds(int(deadline) + MICROSECONDS_PER_MINUTE),
        cutoff,
    )

    assert on_time is DepositStatus.REFUND_DUE
    assert late is DepositStatus.KEPT


@pytest.mark.parametrize("terms", TERMS_TEXTS)
def test_the_terms_speak_every_language_a_deposit_line_speaks(
    terms: LocalizedText,
) -> None:
    for line in (
        DEPOSIT_BOOKING_LINE,
        DEPOSIT_BANQUET_LINE,
        DEPOSIT_BOOKING_REMINDER,
        DEPOSIT_BANQUET_REMINDER,
    ):
        assert set(line.values) <= set(terms.values)
