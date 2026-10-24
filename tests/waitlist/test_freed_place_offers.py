"""A cancellation frees a place: it is held and offered to the first who fits."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    CancelBookingCommand,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.waitlist.offer_jobs import (
    OFFER_FREED_PLACE_JOB,
    STAFF_CHANGE_DELAY_SECONDS,
)
from tests.waitlist.full_evening import DAY, FullEvening

MICROSECONDS_PER_SECOND: int = 1_000_000
HOLD_MICROSECONDS: int = 30 * 60 * MICROSECONDS_PER_SECOND


def cancel_evening(evening: FullEvening, actor_id: UserId | None = None) -> None:
    evening.world.cancel_booking().run(
        CancelBookingCommand(
            business_id=evening.world.business.id,
            booking_id=evening.evening.id,
            contact_id=None if actor_id is not None else evening.giorgi.id,
            language=LanguageTag("ka"),
            actor_id=actor_id,
        )
    )


def times_for(evening: FullEvening, contact_id: ContactId | None) -> list[str]:
    result: AvailabilityResult = evening.world.check_availability().run(
        AvailabilityQuery(
            business_id=evening.world.business.id,
            date=LocalDate(DAY),
            party_size=PartySize(2),
            contact_id=contact_id,
        )
    )
    return [str(slot.time) for slot in result.slots]


def test_a_customer_cancellation_queues_the_offer_at_once() -> None:
    evening = FullEvening()

    cancel_evening(evening)

    [call] = [
        call
        for call in evening.world.job_queue.calls
        if call.job_name == OFFER_FREED_PLACE_JOB
    ]
    assert call.business_id == evening.world.business.id
    assert int(call.run_at or 0) == int(evening.world.clock.now_microseconds())


def test_a_staff_cancellation_waits_for_its_undo() -> None:
    evening = FullEvening()

    cancel_evening(evening, actor_id=UserId())

    [call] = [
        call
        for call in evening.world.job_queue.calls
        if call.job_name == OFFER_FREED_PLACE_JOB
    ]
    delay = int(call.run_at or 0) - int(evening.world.clock.now_microseconds())
    assert delay == STAFF_CHANGE_DELAY_SECONDS * MICROSECONDS_PER_SECOND


def test_the_freed_place_is_held_and_offered_to_the_first_who_fits() -> None:
    evening = FullEvening()
    world = evening.world
    late = world.guest("Late", "en")
    world.join(late, world.telegram_conversation(late), DAY, "22:00", "22:30")
    nino = world.guest("Nino", "ru")
    nino_chat = world.telegram_conversation(nino)
    nino_entry = world.join(nino, nino_chat, DAY, "19:00", "21:00").entry_id
    tamar = world.guest("Tamar", "ka")
    tamar_entry = world.join(
        tamar, world.telegram_conversation(tamar), DAY, "19:00", "21:00"
    ).entry_id

    cancel_evening(evening)
    world.run_offer_jobs()

    offered = world.entry(nino_entry)
    assert offered.status is WaitlistStatus.OFFERED
    assert offered.offer is not None
    assert offered.offer.channel is ChannelKind.TELEGRAM
    assert offered.offer.conversation_id == nino_chat.id
    assert int(offered.offer_expires_at or 0) == (
        int(world.clock.now_microseconds()) + HOLD_MICROSECONDS
    )
    assert world.entry(tamar_entry).status is WaitlistStatus.WAITING
    [text] = world.outbox_texts()
    assert "Salobie Bia" in text and "19:00" in text and "30" in text
    assert "ДА" in text


def test_a_held_place_is_free_only_for_its_holder() -> None:
    evening = FullEvening()
    world = evening.world
    nino = world.guest("Nino", "ru")
    world.join(nino, world.telegram_conversation(nino), DAY, "19:00", "21:00")
    cancel_evening(evening)
    world.run_offer_jobs()

    assert "19:00" not in times_for(evening, None)
    assert "19:00" not in times_for(evening, evening.regular.id)
    assert "19:00" in times_for(evening, nino.id)


def test_nobody_fits_and_the_place_is_simply_free() -> None:
    evening = FullEvening()
    world = evening.world
    crowd = world.guest("Crowd", "ru")
    world.join(crowd, world.telegram_conversation(crowd), DAY, party_size=6)

    cancel_evening(evening)
    world.run_offer_jobs()

    assert world.outbox_texts() == []
    assert "19:00" in times_for(evening, None)


def test_a_guest_reachable_in_no_messenger_is_passed_over() -> None:
    evening = FullEvening()
    world = evening.world
    silent = world.add_contact(world.business, "Silent", None, "ru")
    chat = world.add_conversation(world.business, silent, channel=ChannelKind.PHONE)
    silent_entry = world.join(silent, chat, DAY, "19:00", "21:00").entry_id
    nino = world.guest("Nino", "ru")
    nino_entry = world.join(
        nino, world.telegram_conversation(nino), DAY, "19:00", "21:00"
    ).entry_id

    cancel_evening(evening)
    world.run_offer_jobs()

    assert world.entry(silent_entry).status is WaitlistStatus.WAITING
    assert world.entry(nino_entry).status is WaitlistStatus.OFFERED


def test_a_business_that_turned_its_waitlist_off_offers_nothing() -> None:
    evening = FullEvening()
    world = evening.world
    nino = world.guest("Nino", "ru")
    entry_id = world.join(
        nino, world.telegram_conversation(nino), DAY, "19:00", "21:00"
    ).entry_id
    world.set_waitlist(is_enabled=False)

    cancel_evening(evening)
    world.run_offer_jobs()

    assert world.entry(entry_id).status is WaitlistStatus.WAITING
    assert world.outbox_texts() == []
