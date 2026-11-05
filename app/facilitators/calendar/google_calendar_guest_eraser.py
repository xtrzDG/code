import logging
from collections.abc import Sequence

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_erasure import CalendarGuestErasureFacilitatorContract
from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    CalendarConnectionRepoContract,
    CalendarEventLinkRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.facilitators.calendar.google_access_tokens import fresh_access_token
from app.facilitators.calendar.google_calendar_sync_facilitator import (
    summarize_sync_failure,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar import (
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES

LOGGER: logging.Logger = logging.getLogger(__name__)
UNEXPECTED_ERASURE_ERROR: str = "Unexpected error while erasing a guest's event."


class GoogleCalendarGuestEraser(CalendarGuestErasureFacilitatorContract):
    """
    An erased customer's bookings in the business's Google Calendar (the
    events the mirror wrote, with the guest's name, phone and notes). A
    booking that still takes its time keeps its event, rewritten by the
    mirror from the booking as the erasure left it: the slot stays busy in
    the owner's calendar without the guest. Any other booking's event
    (completed, no-show: the mirror keeps those) is deleted with its link.
    A failure (Google unreachable, access revoked) is logged and recorded
    on the connection as the mirror records its own, so the cabinet shows
    that syncing stopped; it never fails the erasure.
    """

    def __init__(
        self,
        connection_repo: CalendarConnectionRepoContract,
        event_link_repo: CalendarEventLinkRepoContract,
        calendar_client: GoogleCalendarClientContract,
        secret_cipher: SecretCipherAdapterContract,
        mirror: BookingCalendarSyncFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._event_link_repo: CalendarEventLinkRepoContract = event_link_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._mirror: BookingCalendarSyncFacilitatorContract = mirror
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def forget_guest(self, bookings: Sequence[BookingDocument]) -> ErasedRecordCount:
        changed: int = 0
        for booking in bookings:
            if booking.is_sandbox:
                continue

            link: CalendarEventLinkDocument | None = (
                self._event_link_repo.find_by_booking(booking.business_id, booking.id)
            )
            if link is None:
                continue

            if booking.status in BLOCKING_BOOKING_STATUSES:
                # The mirror rewrites the event (it never raises).
                self._mirror.sync(booking)
                changed += 1
            elif self._delete_event(booking, link):
                changed += 1

        return ErasedRecordCount(changed)

    def _delete_event(
        self, booking: BookingDocument, link: CalendarEventLinkDocument
    ) -> bool:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(booking.business_id)
        )
        if connection is None:
            # Disconnected: the platform can reach the calendar no more.
            self._event_link_repo.delete_by_booking(booking.business_id, booking.id)
            return False

        try:
            self._calendar_client.delete_event(
                fresh_access_token(
                    connection,
                    self._connection_repo,
                    self._calendar_client,
                    self._secret_cipher,
                    self._wall_clock.now_unix(),
                ),
                link.calendar_id,
                link.event_id,
            )
        except Exception as error:  # noqa: BLE001 - never fails the erasure
            LOGGER.warning(
                "Erasing the calendar event of booking %s failed: %s",
                booking.id,
                type(error).__name__,
            )
            self._record_failure(booking, str(error) or UNEXPECTED_ERASURE_ERROR)
            return False

        self._event_link_repo.delete_by_booking(booking.business_id, booking.id)
        return True

    def _record_failure(self, booking: BookingDocument, failure: str) -> None:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(booking.business_id)
        )
        if connection is None:
            return

        now: Microseconds = self._wall_clock.now_unix()
        connection.last_sync_error = summarize_sync_failure(failure)
        connection.last_sync_error_at = now
        connection.updated_at = now
        self._connection_repo.save(connection)
