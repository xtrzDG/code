from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.operations import BusinessLockRegistryContract
from app.contracts.repositories.waitlist_repositories import WaitlistEntryRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.schemas.domain.waitlist import WaitlistEntryDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.waitlist.waitlist_release import queue_next_offer

# Entries one run looks at per kind; the rest wait for the next minute.
SWEEP_LIMIT: DocumentQueryLimit = DocumentQueryLimit(500)


class ExpireWaitlistOffersUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job (every minute, across businesses): an offer whose hold ran
    out without an answer ends (EXPIRED, no answer) under the business's
    booking lock, so it never races a "yes" that is booking the place, and
    the place goes to the next customer who fits; an entry whose wanted
    day (or window) is over ends too (EXPIRED, date passed).
    """

    def __init__(
        self,
        waitlist_entry_repo: WaitlistEntryRepoContract,
        lock_registry: BusinessLockRegistryContract,
        job_queue: JobQueueFacilitatorContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        ended: int = 0
        for entry in self._entry_repo.list_lapsed_offers(now, SWEEP_LIMIT):
            with self._lock_registry.lock_for(entry.business_id):
                lapsed = self._entry_repo.update(
                    entry.business_id, entry.id, lambda current: lapse(current, now)
                )

            if lapsed is not None:
                queue_next_offer(self._job_queue, lapsed, now)
                self._announce(lapsed)
                ended += 1

        for entry in self._entry_repo.list_past_waiting(now, SWEEP_LIMIT):
            passed = self._entry_repo.update(
                entry.business_id, entry.id, lambda current: pass_day(current, now)
            )
            if passed is not None:
                self._announce(passed)
                ended += 1

        return JobReport(processed_count=ProcessedItemCount(ended))

    def _announce(self, entry: WaitlistEntryDocument) -> None:
        self._live_events.publish(
            entry.business_id,
            LiveEventKind.WAITLIST_CHANGED,
            (entry.id,),
            is_sandbox=entry.is_sandbox,
        )


def lapse(
    entry: WaitlistEntryDocument, now: Microseconds
) -> WaitlistEntryDocument | None:
    """An offer still held whose hold ran out: no answer."""

    if (
        entry.status is not WaitlistStatus.OFFERED
        or entry.offer_expires_at is None
        or int(entry.offer_expires_at) > int(now)
    ):
        return None

    entry.status = WaitlistStatus.EXPIRED
    entry.end_reason = WaitlistEndReason.NO_ANSWER
    entry.offer_expires_at = None
    entry.ended_at = now
    entry.updated_at = now
    return entry


def pass_day(
    entry: WaitlistEntryDocument, now: Microseconds
) -> WaitlistEntryDocument | None:
    """A wish still waiting whose day (or window) is over."""

    if entry.status is not WaitlistStatus.WAITING or int(entry.waits_until) > int(now):
        return None

    entry.status = WaitlistStatus.EXPIRED
    entry.end_reason = WaitlistEndReason.DATE_PASSED
    entry.ended_at = now
    entry.updated_at = now
    return entry
