from typed_time_provider import Microseconds

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import (
    BookingSystemLink,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemCredentials,
    BookingSystemResource,
)
from app.schemas.dto.calendar_sync.calendar_commands import LinkBookingSystemCommand
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges, due_now
from app.use_cases.calendar_sync.calendar_refusals import calendar_refusal

# Checking a key is one call; the system may be slower than a busy-time read.
KEY_CHECK_SECONDS: BusyTimeFetchSeconds = BusyTimeFetchSeconds(5.0)


class LinkBookingSystemUseCase(
    UseCaseContract[LinkBookingSystemCommand, ResourceCalendarView]
):
    """
    Owners make a resource follow their booking system (Cal.com: an event
    type): its bookings block the resource. The key and the resource are
    checked with the system first (a refused key or a missing event type
    is a 422 with the reason); the key is stored encrypted and never shown
    again. A system linked before is replaced and its busy times
    forgotten. Read right away (2 s); audited.
    """

    def __init__(
        self, changes: CalendarChanges, secret_cipher: SecretCipherAdapterContract
    ) -> None:
        self._changes: CalendarChanges = changes
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: LinkBookingSystemCommand) -> ResourceCalendarView:
        reader = self._changes.reader
        resource: ResourceDocument = reader.resource(
            input_data.business_id, input_data.resource_id
        )
        request = input_data.link
        try:
            described: BookingSystemResource = (
                self._changes.busy_time_sync.describe_booking_system(
                    request.kind,
                    BookingSystemCredentials(
                        api_key=request.api_key,
                        external_resource_id=request.external_resource_id,
                    ),
                    KEY_CHECK_SECONDS,
                )
            )
        except BusyTimeSourceError as error:
            raise calendar_refusal(error.problem.value, str(error)) from error

        now: Microseconds = reader.wall_clock.now_unix()
        linked = BookingSystemLink(
            kind=request.kind,
            external_resource_id=request.external_resource_id,
            external_resource_title=described.title,
            encrypted_api_key=self._secret_cipher.encrypt(
                ChannelSecret(str(request.api_key))
            ),
            added_at=now,
        )

        def link_system(
            link: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument:
            link.booking_system = linked
            due_now(link, now)
            return link

        self._changes.change(resource, link_system, now)
        self._changes.forget(resource, BusyTimeSource.BOOKING_SYSTEM)
        self._changes.audit(resource, input_data.actor_id, AuditAction.UPDATE, now)
        return self._changes.synced_view(resource)
