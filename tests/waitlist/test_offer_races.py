"""
Races for a freed place, decided under the business's booking lock: the
holder's late yes against another guest booking the same table, two runs of
one offer job, and a yes at the moment the hold runs out.
"""

import threading
from collections.abc import Callable
from functools import partial

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB
from tests.waitlist.full_evening import DAY
from tests.waitlist.offered_evening import OfferedEvening

ROUNDS: int = 12


def run_together(*actions: Callable[[], object]) -> list[object]:
    """Start the actions at the same moment; their results or errors, in order."""

    barrier = threading.Barrier(len(actions))
    results: list[object] = [None] * len(actions)

    def run(index: int, action: Callable[[], object]) -> None:
        barrier.wait()
        try:
            results[index] = action()
        except ApplicationError as error:
            results[index] = error

    threads = [
        threading.Thread(target=run, args=(index, action))
        for index, action in enumerate(actions)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    return results


def walk_in_booking(evening: OfferedEvening) -> Callable[[], object]:
    guest = evening.world.guest("Walk-in", "en")
    command = CreateBookingCommand(
        business_id=evening.world.business.id,
        contact_id=guest.id,
        contact_name=ContactName("Walk-in"),
        date=LocalDate(DAY),
        time=LocalTimeOfDay("19:00"),
        party_size=PartySize(2),
        source_channel=ChannelKind.TELEGRAM,
        language=LanguageTag("en"),
    )
    return partial(evening.world.create_booking().run, command)


def test_a_late_yes_and_a_walk_in_never_both_get_the_table() -> None:
    for _ in range(ROUNDS):
        evening = OfferedEvening()
        evening.pass_minutes(31)
        evening.world.expire_due()
        answer = evening.world.answer_offer()
        turn = evening.world.turn(evening.nino, evening.nino_chat, "да")

        yes, walk_in = run_together(partial(answer.run, turn), walk_in_booking(evening))

        [booking] = evening.evening_bookings()
        holder_won: bool = booking.contact_id == evening.nino.id
        assert holder_won == isinstance(walk_in, ApplicationError)
        assert yes is not None


def test_a_held_place_refuses_a_walk_in_while_the_hold_lasts() -> None:
    evening = OfferedEvening()

    [walk_in] = run_together(walk_in_booking(evening))

    assert isinstance(walk_in, ApplicationError)
    assert evening.evening_bookings() == []


def test_two_runs_of_one_offer_job_hold_the_place_once() -> None:
    for _ in range(ROUNDS):
        evening = OfferedEvening()
        evening.world.answer(evening.nino, evening.nino_chat, "нет")
        [call] = [
            call
            for call in evening.world.job_queue.calls
            if call.job_name == OFFER_FREED_PLACE_JOB
        ]
        evening.world.job_queue.calls.clear()
        job = QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=call.job_name,
            payload=call.payload,
            business_id=call.business_id,
        )
        first = evening.world.offer_freed_place()
        second = evening.world.offer_freed_place()

        run_together(partial(first.run, job), partial(second.run, job))

        tamar = evening.world.entry(evening.tamar_entry)
        assert tamar.status is WaitlistStatus.OFFERED
        assert len(evening.world.outbox_texts()) == 2


def test_a_yes_as_the_hold_runs_out_leaves_one_owner() -> None:
    for _ in range(ROUNDS):
        evening = OfferedEvening()
        evening.pass_minutes(30)
        answer = evening.world.answer_offer()
        turn = evening.world.turn(evening.nino, evening.nino_chat, "да")

        run_together(partial(answer.run, turn), evening.world.expire_due)
        evening.world.run_offer_jobs()

        bookings = evening.evening_bookings()
        tamar = evening.world.entry(evening.tamar_entry)
        assert len(bookings) <= 1
        if bookings:
            assert bookings[0].contact_id == evening.nino.id
            assert tamar.status is WaitlistStatus.WAITING
        else:
            assert tamar.status is WaitlistStatus.OFFERED


def test_a_yes_books_only_under_the_business_lock() -> None:
    evening = OfferedEvening()
    answer = evening.world.answer_offer()
    turn = evening.world.turn(evening.nino, evening.nino_chat, "да")
    worker = threading.Thread(target=partial(answer.run, turn))

    with evening.world.lock_registry.lock_for(evening.world.business.id):
        worker.start()
        worker.join(timeout=0.3)
        assert worker.is_alive()
        assert evening.evening_bookings() == []

    worker.join(timeout=10)
    [booking] = evening.evening_bookings()
    assert booking.contact_id == evening.nino.id


def test_an_offer_holds_the_place_only_under_the_business_lock() -> None:
    evening = OfferedEvening()
    evening.world.answer(evening.nino, evening.nino_chat, "нет")
    worker = threading.Thread(target=evening.world.run_offer_jobs)

    with evening.world.lock_registry.lock_for(evening.world.business.id):
        worker.start()
        worker.join(timeout=0.3)
        assert worker.is_alive()
        assert evening.world.entry(evening.tamar_entry).status is (
            WaitlistStatus.WAITING
        )

    worker.join(timeout=10)
    assert evening.world.entry(evening.tamar_entry).status is WaitlistStatus.OFFERED
