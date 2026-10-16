"""
A freed place is offered only when the calendars outside the platform leave
it free, as availability reads them: a Cal.com booking made over Giorgi's
cancelled evening keeps the waiting customer waiting, a busy time elsewhere
does not, and the stale busy times are read again before the check.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.calendar_sync import BusyBlock, CalendarBusyTimesDocument
from app.schemas.typings.calendar_sync.constrained_integers import (
    BusyEndsAtUnixSeconds,
    BusyStartsAtUnixSeconds,
)
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId
from app.utilities.calendar_sync.calendar_sync_keys import busy_times_id_of
from tests.waitlist.full_evening import DAY, FullEvening
from tests.waitlist.test_freed_place_offers import cancel_evening

HOUR: int = 60 * 60


def busy_in_cal_com(evening: FullEvening, starts_at: int, ends_at: int) -> None:
    """The table's booking system reports a booking of its own then."""

    world = evening.world
    resource_id = evening.evening.resource_id
    now: Microseconds = world.clock.now_microseconds()
    world.busy_times_repo.store_if_newer(
        CalendarBusyTimesDocument(
            id=busy_times_id_of(resource_id, BusyTimeSource.BOOKING_SYSTEM),
            business_id=world.business.id,
            resource_id=resource_id,
            source=BusyTimeSource.BOOKING_SYSTEM,
            blocks=[
                BusyBlock(
                    starts_at=BusyStartsAtUnixSeconds(starts_at),
                    ends_at=BusyEndsAtUnixSeconds(ends_at),
                )
            ],
            covers_until=BusyEndsAtUnixSeconds(ends_at + 30 * 24 * HOUR),
            fetched_at=now,
            created_at=now,
            updated_at=now,
        )
    )


def nino_waits(evening: FullEvening) -> WaitlistEntryId:
    world = evening.world
    nino = world.guest("Nino", "ru")
    return world.join(
        nino, world.telegram_conversation(nino), DAY, "19:00", "21:00"
    ).entry_id


def test_a_place_cal_com_took_meanwhile_is_not_offered() -> None:
    evening = FullEvening()
    entry = nino_waits(evening)
    starts = int(evening.evening.starts_at)

    cancel_evening(evening)
    busy_in_cal_com(evening, starts + HOUR, starts + 2 * HOUR)
    evening.world.run_offer_jobs()

    assert evening.world.entry(entry).status is WaitlistStatus.WAITING
    assert evening.world.outbox_texts() == []
    assert (evening.world.business.id, 2.0) in (
        evening.world.busy_time_sync.stale_refreshes
    )


def test_a_busy_time_elsewhere_leaves_the_place_free() -> None:
    evening = FullEvening()
    entry = nino_waits(evening)
    ends = int(evening.evening.ends_at)

    cancel_evening(evening)
    busy_in_cal_com(evening, ends + 3 * HOUR, ends + 4 * HOUR)
    evening.world.run_offer_jobs()

    assert evening.world.entry(entry).status is WaitlistStatus.OFFERED
