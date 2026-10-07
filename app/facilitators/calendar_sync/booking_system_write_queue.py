import logging

from app.contracts.calendar_sync import ResourceCalendarLinkRepoContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.operations import BookingCalendarSyncFacilitatorContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.utilities.calendar_sync.booking_system_jobs import (
    WRITE_BOOKING_SYSTEM_BOOKING_JOB,
    booking_system_write_key,
    encode_booking_system_write,
)

logger: logging.Logger = logging.getLogger(__name__)


class BookingSystemWriteQueue(BookingCalendarSyncFacilitatorContract):
    """
    Queues the write of a booking to the booking system its resource
    follows (Cal.com) instead of calling it while the customer waits: one
    `write_booking_system_booking` job per change, the jobs of one booking
    run one at a time in order, with the queue's retries. Each job makes
    the booking system show the booking as it is then (written, moved or
    cancelled). A booking of a resource that follows no booking system and
    was never written there is left alone, and so is every test booking.
    Never raises: the booking is stored whatever its mirror does.
    """

    def __init__(
        self,
        link_repo: ResourceCalendarLinkRepoContract,
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._link_repo: ResourceCalendarLinkRepoContract = link_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def sync(self, booking: BookingDocument) -> None:
        if booking.is_sandbox:
            return

        try:
            if booking.booking_system_booking is None and not self._follows(booking):
                return

            self._job_queue.enqueue(
                WRITE_BOOKING_SYSTEM_BOOKING_JOB,
                encode_booking_system_write(booking.business_id, booking.id),
                booking.business_id,
                lane=JobLane.DEFAULT,
                serial_key=booking_system_write_key(booking.id),
            )
        except Exception:
            logger.exception(
                "The booking system write of booking %s was not queued.", booking.id
            )

    def _follows(self, booking: BookingDocument) -> bool:
        link: ResourceCalendarLinkDocument | None = self._link_repo.get(
            booking.business_id, booking.resource_id
        )
        return link is not None and link.booking_system is not None
