import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.deposits import DepositSettlementFacilitatorContract
from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.operations import BookingCalendarSyncFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import DepositNoticeKind, DepositStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.deposits import DepositRequestDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.deposits.deposit_hold_release import DepositHoldRelease, ReleasedHold
from app.use_cases.deposits.deposit_notice_texts import DepositNoticeTexts
from app.use_cases.deposits.deposit_notices import DepositNotices

LOGGER: logging.Logger = logging.getLogger(__name__)
# Deposits one run looks at per kind; the rest wait for the next minute.
SWEEP_LIMIT: DocumentQueryLimit = DocumentQueryLimit(500)


class SweepDepositsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job (every minute, across businesses), three sweeps:

    1. holds that ran out unpaid are released (`DepositHoldRelease`, under
       the business's booking lock): the deposit EXPIRED, the booking
       cancelled, its place offered to the waitlist, its calendar event
       removed, the customer told (outbox);
    2. reminders due halfway through a hold go once (outbox), with the same
       link, and are not looked at again;
    3. paid deposits of bookings that ended are settled after the cabinet's
       undo window (REFUND_DUE or KEPT; staff are told of a refund).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        deposit_request_repo: DepositRequestRepoContract,
        deposit_settings_repo: DepositSettingsRepoContract,
        booking_repo: BookingRepoContract,
        hold_release: DepositHoldRelease,
        notices: DepositNotices,
        notice_texts: DepositNoticeTexts,
        settlement: DepositSettlementFacilitatorContract,
        growth: GrowthBookingsFacilitatorContract,
        calendar_sync: BookingCalendarSyncFacilitatorContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._request_repo: DepositRequestRepoContract = deposit_request_repo
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._hold_release: DepositHoldRelease = hold_release
        self._notices: DepositNotices = notices
        self._notice_texts: DepositNoticeTexts = notice_texts
        self._settlement: DepositSettlementFacilitatorContract = settlement
        self._growth: GrowthBookingsFacilitatorContract = growth
        self._calendar_sync: BookingCalendarSyncFacilitatorContract = calendar_sync
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        done: int = 0
        for request in self._request_repo.list_lapsed_holds(now, SWEEP_LIMIT):
            released: ReleasedHold | None = self._hold_release.release(request, now)
            if released is not None:
                self._after_release(released, now)
                done += 1

        for request in self._request_repo.list_due_reminders(now, SWEEP_LIMIT):
            if self._remind(request, now):
                done += 1

        for request in self._request_repo.list_due_settlements(now, SWEEP_LIMIT):
            if self._settlement.settle(request.business_id, request.id, now):
                done += 1

        return JobReport(processed_count=ProcessedItemCount(done))

    def _after_release(self, released: ReleasedHold, now: Microseconds) -> None:
        if released.lead is not None:
            self._live_events.publish(
                released.lead.business_id,
                LiveEventKind.LEAD_CHANGED,
                (released.lead.id,),
                is_sandbox=released.lead.is_sandbox,
            )

        booking = released.booking
        if booking is None or not released.was_booking_held:
            return

        self._live_events.publish(
            booking.business_id,
            LiveEventKind.BOOKING_CHANGED,
            (booking.id,),
            is_sandbox=booking.is_sandbox,
        )
        if booking.is_sandbox:
            return

        self._calendar_sync.sync(booking)
        self._growth.notice_freed(
            booking,
            FreedPlace(
                freed_booking_id=booking.id,
                resource_id=booking.resource_id,
                starts_at=booking.starts_at,
                ends_at=booking.ends_at,
            ),
            now,
        )
        business = self._business_repo.get(booking.business_id)
        if business is not None:
            self._notices.send(
                business,
                released.request,
                DepositNoticeKind.RELEASED,
                self._notice_texts.released(business, released.request, booking),
                now,
            )

    def _remind(self, request: DepositRequestDocument, now: Microseconds) -> bool:
        """Mark the reminder sent first, so a second worker never sends it again."""

        def mark(stored: DepositRequestDocument) -> DepositRequestDocument | None:
            if (
                stored.status is not DepositStatus.AWAITING
                or stored.reminder_due_at is None
            ):
                return None

            stored.reminder_due_at = None
            stored.reminder_sent_at = now
            stored.updated_at = now
            return stored

        claimed = self._request_repo.update(request.business_id, request.id, mark)
        business = self._business_repo.get(request.business_id)
        settings = self._settings_repo.get_by_business(request.business_id)
        if claimed is None or business is None or settings is None:
            return False

        booking = (
            None
            if claimed.booking_id is None
            else self._booking_repo.get(business.id, claimed.booking_id)
        )
        text = self._notice_texts.reminder(business, settings, claimed, booking, now)
        if text is None:
            return False

        try:
            return self._notices.send(
                business, claimed, DepositNoticeKind.REMINDER, text, now
            )
        except Exception:
            LOGGER.exception("The reminder of deposit %s was not queued.", claimed.id)
            return False
