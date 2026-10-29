"""The minute's sweep: a hold that ran out, a day that is over."""

from datetime import datetime

from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB
from tests.waitlist.full_evening import DAY, FullEvening
from tests.waitlist.offered_evening import OfferedEvening


def offer_jobs(evening: FullEvening) -> int:
    return [call.job_name for call in evening.world.job_queue.calls].count(
        OFFER_FREED_PLACE_JOB
    )


def test_a_hold_that_has_not_run_out_stays() -> None:
    evening = OfferedEvening()
    evening.pass_minutes(29)

    report = evening.world.expire_due()

    assert int(report.processed_count) == 0
    assert evening.world.entry(evening.nino_entry).status is WaitlistStatus.OFFERED


def test_a_lapsed_hold_ends_unanswered_and_the_place_goes_on() -> None:
    evening = OfferedEvening()
    evening.pass_minutes(30)

    report = evening.world.expire_due()

    assert int(report.processed_count) == 1
    entry = evening.world.entry(evening.nino_entry)
    assert entry.status is WaitlistStatus.EXPIRED
    assert entry.end_reason is WaitlistEndReason.NO_ANSWER
    assert entry.offer_expires_at is None
    assert offer_jobs(evening) == 1
    evening.world.run_offer_jobs()
    assert evening.world.entry(evening.tamar_entry).status is WaitlistStatus.OFFERED
    assert len(evening.world.outbox_texts()) == 2


def test_a_second_sweep_ends_nothing_twice() -> None:
    evening = OfferedEvening()
    evening.pass_minutes(45)
    evening.world.expire_due()

    report = evening.world.expire_due()

    assert int(report.processed_count) == 0
    assert offer_jobs(evening) == 1


def test_a_wish_whose_day_is_over_ends() -> None:
    evening = FullEvening()
    nino = evening.world.guest("Nino", "ru")
    entry_id = evening.world.join(
        nino, evening.world.telegram_conversation(nino), DAY, "19:00", "21:00"
    ).entry_id
    evening.world.clock.move_to(datetime.fromisoformat("2026-10-07T21:30:00+04:00"))

    evening.world.expire_due()

    entry = evening.world.entry(entry_id)
    assert entry.status is WaitlistStatus.EXPIRED
    assert entry.end_reason is WaitlistEndReason.DATE_PASSED
