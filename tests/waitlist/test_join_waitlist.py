"""Joining the waitlist (model tool join_waitlist) when a day is full."""

import pytest

from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from tests.waitlist.full_evening import DAY, FullEvening


def availability(
    evening: FullEvening, day: str = DAY, party_size: int = 2
) -> AvailabilityResult:
    return evening.world.check_availability().run(
        AvailabilityQuery(
            business_id=evening.world.business.id,
            date=LocalDate(day),
            party_size=PartySize(party_size),
        )
    )


def test_a_full_day_offers_the_waitlist_and_a_guest_joins_it() -> None:
    evening = FullEvening()
    nino = evening.world.guest("Nino", "ru")
    chat = evening.world.telegram_conversation(nino)

    result = availability(evening)
    receipt = evening.world.join(nino, chat, DAY, "19:00", "21:00")

    assert result.slots == []
    assert result.is_waitlist_open is True
    entry = evening.world.entry(receipt.entry_id)
    assert entry.status is WaitlistStatus.WAITING
    assert (str(entry.time_from), str(entry.time_to)) == ("19:00", "21:00")
    assert str(entry.contact_name) == "Nino"
    assert int(receipt.hold_minutes) == 30
    assert receipt.is_already_waiting is False


def test_joining_the_same_day_again_updates_the_wish() -> None:
    evening = FullEvening()
    nino = evening.world.guest("Nino", "ru")
    chat = evening.world.telegram_conversation(nino)
    first = evening.world.join(nino, chat, DAY, "19:00", "21:00", party_size=2)

    second = evening.world.join(nino, chat, DAY, "18:00", "22:00", party_size=3)

    assert second.entry_id == first.entry_id
    assert second.is_already_waiting is True
    entry = evening.world.entry(first.entry_id)
    assert (str(entry.time_from), int(entry.party_size)) == ("18:00", 3)


def test_a_day_with_a_fitting_free_time_is_refused() -> None:
    evening = FullEvening()
    nino = evening.world.guest("Nino", "ru")
    chat = evening.world.telegram_conversation(nino)

    with pytest.raises(ValidationFailedError):
        evening.world.join(nino, chat, "2026-10-08", "19:00", "21:00")


def test_a_business_without_a_waitlist_offers_none() -> None:
    evening = FullEvening()
    evening.world.set_waitlist(is_enabled=False)
    nino = evening.world.guest("Nino", "ru")
    chat = evening.world.telegram_conversation(nino)

    assert availability(evening).is_waitlist_open is False
    with pytest.raises(ValidationFailedError):
        evening.world.join(nino, chat, DAY)


def test_a_closed_day_offers_no_waitlist() -> None:
    evening = FullEvening()
    evening.world.add_exception(evening.world.business, "2026-10-09")

    result = availability(evening, "2026-10-09")

    assert result.is_open_on_date is False
    assert result.is_waitlist_open is False


def test_a_guest_waits_for_three_days_at_most() -> None:
    evening = FullEvening()
    nino = evening.world.guest("Nino", "ru")
    chat = evening.world.telegram_conversation(nino)
    for day in ("2026-10-10", "2026-10-11", "2026-10-12"):
        for table in (evening.world.table_for_four, evening.world.table_for_eight):
            evening.world.add_booking(
                evening.world.business,
                table,
                evening.regular,
                f"{day}T12:00:00+04:00",
                f"{day}T23:00:00+04:00",
            )
        evening.world.join(nino, chat, day)

    with pytest.raises(ValidationFailedError):
        evening.world.join(nino, chat, DAY)


def test_a_past_day_cannot_be_waited_for() -> None:
    evening = FullEvening()
    nino = evening.world.guest("Nino", "ru")
    chat = evening.world.telegram_conversation(nino)

    with pytest.raises(ValidationFailedError):
        evening.world.join(nino, chat, "2026-10-04")
