import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    BookingSystemConnectorContract,
    BookingSystemConnectorRegistryContract,
    ResourceCalendarLinkRepoContract,
)
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar_sync import BookingSystemBookingRef, BookingSystemLink
from app.schemas.dto.calendar_sync.booking_writes import BookingSystemWriteJob
from app.schemas.dto.calendar_sync.busy_reads import BookingSystemCredentials
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.calendar_sync.strings import BookingSystemApiKey
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.calendar_sync.booking_system_links import (
    WriteCall,
    keep_written,
    record_write,
    system_of,
)
from app.use_cases.shared.business_access import require_business
from app.utilities.calendar_sync.booking_system_jobs import (
    decode_booking_system_write,
)
from app.utilities.calendar_sync.booking_system_writes import (
    FINAL_PROBLEMS,
    booking_system_draft,
    is_wanted,
    is_written_as_now,
    written_ref,
)
from app.utilities.calendar_sync.busy_windows import BACKGROUND_READ_SECONDS

LOGGER: logging.Logger = logging.getLogger(__name__)


class WriteBookingSystemBookingUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    The `write_booking_system_booking` job: make the booking system of a
    booking's resource (Cal.com) show the booking as it is now.

    - A real booking that takes its time, of a resource that follows a
      booking system, is written there (the guest's name, the business's
      zone, the customer's language, marked as the platform's) and the
      system's id is kept on the booking. A write repeated after one that
      went through but was not kept finds that one instead of writing a
      second.
    - A booking written before that was cancelled, moved to another time
      or resource, or whose resource follows no system any more, is
      cancelled there first (with the key of the resource it was written
      for; without that key it stays there as it is).

    Every outcome is recorded on the resource's calendar settings (the
    card shows the last failure with its reason until a write goes
    through). A failure a retry may fix (a timeout, Cal.com unreachable or
    in error) raises for the queue's retries; a refused key or a gone event
    type does not, nor does the last attempt.
    """

    def __init__(
        self,
        booking_repo: BookingRepoContract,
        link_repo: ResourceCalendarLinkRepoContract,
        contact_repo: ContactRepoContract,
        business_repo: BusinessRepoContract,
        connectors: BookingSystemConnectorRegistryContract,
        secret_cipher: SecretCipherAdapterContract,
        text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._booking_repo: BookingRepoContract = booking_repo
        self._link_repo: ResourceCalendarLinkRepoContract = link_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._connectors: BookingSystemConnectorRegistryContract = connectors
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        job: BookingSystemWriteJob = decode_booking_system_write(input_data.payload)
        booking: BookingDocument | None = self._booking_repo.get(
            job.business_id, job.booking_id
        )
        if booking is None:
            return JobReport()

        system: BookingSystemLink | None = system_of(
            self._link_repo, booking.business_id, booking.resource_id
        )
        written: BookingSystemBookingRef | None = booking.booking_system_booking
        try:
            if written is not None and not (
                is_wanted(booking, system)
                and is_written_as_now(written, booking, system)
            ):
                self._cancel(booking, written)
                written = None
            if written is None and system is not None and is_wanted(booking, system):
                self._write(booking, system)
        except BusyTimeSourceError as error:
            if error.problem in FINAL_PROBLEMS or input_data.is_final_attempt:
                return JobReport()
            raise

        return JobReport(processed_count=ProcessedItemCount(1))

    def _cancel(
        self, booking: BookingDocument, written: BookingSystemBookingRef
    ) -> None:
        """Cancel the booking written before; then forget it on the booking."""

        system: BookingSystemLink | None = system_of(
            self._link_repo, booking.business_id, written.resource_id
        )
        if system is None or system.kind is not written.kind:
            LOGGER.info(
                "Booking %s stays in its booking system: its resource follows it "
                "no more.",
                booking.id,
            )
        else:
            self._attempt(
                booking,
                written.resource_id,
                lambda connector, credentials: connector.cancel_booking(
                    credentials, written.booking_id, BACKGROUND_READ_SECONDS
                ),
                system,
            )
        keep_written(self._booking_repo, booking, written, None)

    def _write(self, booking: BookingDocument, system: BookingSystemLink) -> None:
        business = require_business(self._business_repo, booking.business_id)
        draft = booking_system_draft(
            booking,
            self._contact_repo.get(booking.business_id, booking.contact_id),
            business,
            self._text_resolver,
        )

        def write(
            connector: BookingSystemConnectorContract,
            credentials: BookingSystemCredentials,
        ) -> None:
            found = connector.find_booking(credentials, draft, BACKGROUND_READ_SECONDS)
            external_id = (
                found
                or connector.create_booking(
                    credentials, draft, BACKGROUND_READ_SECONDS
                ).booking_id
            )
            ref = written_ref(system, booking, external_id, self._wall_clock.now_unix())
            keep_written(self._booking_repo, booking, None, ref)

        self._attempt(booking, booking.resource_id, write, system)

    def _attempt(
        self,
        booking: BookingDocument,
        resource_id: ResourceId,
        call: WriteCall,
        system: BookingSystemLink,
    ) -> None:
        """Run one call to the system and record how it went (re-raised)."""

        credentials = BookingSystemCredentials(
            api_key=BookingSystemApiKey(
                str(self._secret_cipher.decrypt(system.encrypted_api_key))
            ),
            external_resource_id=system.external_resource_id,
        )
        try:
            call(self._connectors.connector_for(system.kind), credentials)
        except BusyTimeSourceError as error:
            LOGGER.warning(
                "Booking %s was not written to its booking system: %s",
                booking.id,
                error.problem.value,
            )
            record_write(
                self._link_repo,
                booking.business_id,
                resource_id,
                self._wall_clock.now_unix(),
                error,
            )
            raise

        record_write(
            self._link_repo,
            booking.business_id,
            resource_id,
            self._wall_clock.now_unix(),
            None,
        )
