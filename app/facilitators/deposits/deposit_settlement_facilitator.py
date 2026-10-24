import logging

from typed_time_provider import Microseconds

from app.contracts.deposits import DepositSettlementFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
    DepositSettingsRepoContract,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositStatus
from app.schemas.constants.notifications import StaffAlertEvent, StaffLinkTarget
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.booleans import IsStaffCancellation
from app.schemas.typings.deposits.constrained_integers import DepositRefundCutoffHours
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.notifications.constrained_strings import (
    PushNotificationTag,
    StaffAlertSubject,
)
from app.utilities.deposits.booking_deposit_state import show_deposit
from app.utilities.deposits.deposit_refund_texts import DepositRefundTexts
from app.utilities.deposits.deposit_settlement import settle_after, settled_status
from app.utilities.scheduling.zoned_time import load_time_zone, to_local_moment

LOGGER: logging.Logger = logging.getLogger(__name__)
ENDED_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CANCELLED, BookingStatus.NO_SHOW}
)
DEFAULT_REFUND_CUTOFF: DepositRefundCutoffHours = DepositRefundCutoffHours(24)


class DepositSettlementFacilitator(DepositSettlementFacilitatorContract):
    """
    The deposit's side of a booking that ended (cancelled, no-show), told
    by every booking change that frees a place: an unpaid deposit is
    CANCELLED; a paid one is settled at once for the customer's own
    cancellation and after the undo window for staff's (the minute's sweep
    settles it). A deposit to refund is a staff alert (bookings), with the
    amount and the reference to find it by. Every write is one step on the
    document as stored, so it never crosses a payment marked or a hold
    released.
    """

    def __init__(
        self,
        deposit_request_repo: DepositRequestRepoContract,
        deposit_settings_repo: DepositSettingsRepoContract,
        booking_repo: BookingRepoContract,
        business_repo: BusinessRepoContract,
        staff_alerts: StaffAlertFacilitatorContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._request_repo: DepositRequestRepoContract = deposit_request_repo
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def notice_booking_ended(
        self,
        booking: BookingDocument,
        now: Microseconds,
        is_staff_change: IsStaffCancellation = False,
    ) -> None:
        try:
            self._notice(booking, now, is_staff_change)
        except Exception:
            LOGGER.exception("The deposit of booking %s was not settled.", booking.id)

    def settle(
        self,
        business_id: BusinessId,
        request_id: DepositRequestId,
        now: Microseconds,
    ) -> DepositRequestDocument | None:
        request = self._request_repo.get(business_id, request_id)
        if request is None or request.booking_id is None:
            return None

        booking = self._booking_repo.get(business_id, request.booking_id)
        settings = self._settings_repo.get_by_business(business_id)
        decided: DepositStatus = settled_status(
            None if booking is None else booking.status,
            None if booking is None else booking.starts_at,
            request.cancelled_at,
            DEFAULT_REFUND_CUTOFF if settings is None else settings.refund_cutoff_hours,
        )

        def decide(stored: DepositRequestDocument) -> DepositRequestDocument | None:
            if stored.status is not DepositStatus.PAID or stored.settle_after is None:
                return None

            stored.status = decided
            stored.settle_after = None
            stored.settled_at = None if decided is DepositStatus.PAID else now
            if decided is DepositStatus.PAID:
                stored.cancelled_at = None
            stored.updated_at = now
            return stored

        settled = self._request_repo.update(business_id, request_id, decide)
        if settled is None:
            return None

        self._show_on_booking(settled, now)
        if settled.status is DepositStatus.REFUND_DUE and booking is not None:
            self._alert_refund(settled, booking)
        return settled

    def _notice(
        self, booking: BookingDocument, now: Microseconds, is_staff_change: bool
    ) -> None:
        if booking.deposit is None or booking.status not in ENDED_STATUSES:
            return

        request_id: DepositRequestId = booking.deposit.request_id

        def end(stored: DepositRequestDocument) -> DepositRequestDocument | None:
            if stored.status is DepositStatus.AWAITING:
                stored.status = DepositStatus.CANCELLED
                stored.reminder_due_at = None
            elif stored.status is DepositStatus.PAID and stored.settle_after is None:
                stored.settle_after = settle_after(now, is_staff_change)
            else:
                return None

            if booking.status is BookingStatus.CANCELLED:
                stored.cancelled_at = now
            stored.updated_at = now
            return stored

        ended = self._request_repo.update(booking.business_id, request_id, end)
        if ended is None:
            return

        self._show_on_booking(ended, now)
        if ended.status is DepositStatus.PAID and not is_staff_change:
            self.settle(booking.business_id, request_id, now)

    def _show_on_booking(
        self, request: DepositRequestDocument, now: Microseconds
    ) -> None:
        if request.booking_id is None:
            return

        def show(booking: BookingDocument) -> BookingDocument | None:
            if booking.deposit is None or booking.deposit.request_id != request.id:
                return None

            return show_deposit(booking, request, now)

        self._booking_repo.update(request.business_id, request.booking_id, show)

    def _alert_refund(
        self, request: DepositRequestDocument, booking: BookingDocument
    ) -> None:
        business = self._business_repo.get(request.business_id)
        if business is None or request.is_sandbox:
            return

        zone = load_time_zone(business.timezone)
        self._staff_alerts.alert(
            business,
            StaffAlert(
                business_id=business.id,
                event=StaffAlertEvent.BOOKING,
                target=StaffLinkTarget.BOOKING,
                booking_id=booking.id,
                tag=PushNotificationTag(f"deposit_refund:{request.id}"),
                subject=StaffAlertSubject(f"deposit_refund:{request.id}"),
            ),
            DepositRefundTexts(
                self._resolver,
                business.name,
                Money(
                    amount_minor=MoneyAmountMinor(int(request.amount_minor)),
                    currency_code=request.currency_code,
                ),
                request.reference,
                to_local_moment(int(booking.starts_at), zone),
                zone,
            ),
        )
