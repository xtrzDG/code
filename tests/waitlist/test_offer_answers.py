"""The waiting guest's yes or no to the place held for them."""

from app.schemas.constants.bookings import BookingOrigin
from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB
from tests.waitlist.offered_evening import OfferedEvening


def test_yes_books_the_held_place_as_the_waitlists() -> None:
    evening = OfferedEvening()

    reply = evening.world.answer(evening.nino, evening.nino_chat, "Да!")

    assert reply is not None and reply.booking_id is not None
    [booking] = evening.evening_bookings()
    assert booking.id == reply.booking_id
    assert booking.contact_id == evening.nino.id
    assert booking.origin is BookingOrigin.WAITLIST
    entry = evening.world.entry(evening.nino_entry)
    assert entry.status is WaitlistStatus.BOOKED
    assert entry.booking_id == booking.id
    [confirmation] = evening.world.confirmations.requests
    assert confirmation.booking_id == booking.id


def test_no_lets_the_place_go_to_the_next_guest() -> None:
    evening = OfferedEvening()

    reply = evening.world.answer(evening.nino, evening.nino_chat, "нет, спасибо")

    assert reply is not None and reply.booking_id is None
    entry = evening.world.entry(evening.nino_entry)
    assert entry.status is WaitlistStatus.EXPIRED
    assert entry.end_reason is WaitlistEndReason.DECLINED
    assert [call.job_name for call in evening.world.job_queue.calls].count(
        OFFER_FREED_PLACE_JOB
    ) == 1
    evening.world.run_offer_jobs()
    assert evening.world.entry(evening.tamar_entry).status is WaitlistStatus.OFFERED


def test_any_other_message_goes_to_the_assistant() -> None:
    evening = OfferedEvening()

    reply = evening.world.answer(evening.nino, evening.nino_chat, "А парковка есть?")

    assert reply is None
    assert evening.world.entry(evening.nino_entry).status is WaitlistStatus.OFFERED


def test_a_yes_in_another_conversation_answers_nothing() -> None:
    evening = OfferedEvening()
    other_chat = evening.world.telegram_conversation(evening.nino)

    assert evening.world.answer(evening.nino, other_chat, "да") is None
    assert evening.evening_bookings() == []


def test_the_next_guest_cannot_answer_an_offer_made_to_someone_else() -> None:
    evening = OfferedEvening()

    assert evening.world.answer(evening.tamar, evening.tamar_chat, "კი") is None
    assert evening.evening_bookings() == []


def test_a_late_yes_still_books_the_place_while_nobody_took_it() -> None:
    evening = OfferedEvening()
    evening.pass_minutes(31)
    evening.world.expire_due()

    reply = evening.world.answer(evening.nino, evening.nino_chat, "да")

    assert reply is not None and reply.booking_id is not None
    assert evening.world.entry(evening.nino_entry).status is WaitlistStatus.BOOKED


def test_a_late_yes_after_the_place_went_to_the_next_guest_waits_on() -> None:
    evening = OfferedEvening()
    evening.pass_minutes(31)
    evening.world.expire_due()
    evening.world.run_offer_jobs()

    reply = evening.world.answer(evening.nino, evening.nino_chat, "да")

    assert reply is not None and reply.booking_id is None
    assert evening.evening_bookings() == []
    assert evening.world.entry(evening.nino_entry).status is WaitlistStatus.WAITING
    assert evening.world.entry(evening.tamar_entry).status is WaitlistStatus.OFFERED
