from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import (
    BusySourceStatus,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.calendar_commands import LinkGoogleCalendarCommand
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.schemas.typings.bookings.strings import ExternalCalendarId
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges, due_now
from app.use_cases.calendar_sync.calendar_refusals import calendar_refusal

MAX_CALENDAR_ID_LENGTH: int = 320


class LinkGoogleCalendarUseCase(
    UseCaseContract[LinkGoogleCalendarCommand, ResourceCalendarView]
):
    """
    Owners link a Google calendar to a resource (`ResourceDocument.
    external_calendar_id`): its busy times, read through the business's
    Google connection, block the resource's slots. A calendar linked
    before is replaced and its busy times forgotten. The calendar is read
    right away (2 s); audited.
    """

    def __init__(self, changes: CalendarChanges) -> None:
        self._changes: CalendarChanges = changes

    def run(self, input_data: LinkGoogleCalendarCommand) -> ResourceCalendarView:
        calendar_id: str = str(input_data.calendar_id).strip()
        if not calendar_id or len(calendar_id) > MAX_CALENDAR_ID_LENGTH:
            raise calendar_refusal("calendar_invalid", "Choose a calendar to link.")

        reader = self._changes.reader
        resource: ResourceDocument = reader.resource(
            input_data.business_id, input_data.resource_id
        )
        now: Microseconds = reader.wall_clock.now_unix()
        replaced: bool = (
            resource.external_calendar_id is not None
            and str(resource.external_calendar_id) != calendar_id
        )
        resource.external_calendar_id = ExternalCalendarId(calendar_id)
        resource.updated_at = now
        reader.resource_repo.save(resource)

        def link_google(
            link: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument:
            if replaced or link.google_status is None:
                link.google_status = BusySourceStatus()
            due_now(link, now)
            return link

        self._changes.change(resource, link_google, now)
        if replaced:
            self._changes.forget(resource, BusyTimeSource.GOOGLE)
        self._changes.audit(resource, input_data.actor_id, AuditAction.UPDATE, now)
        return self._changes.synced_view(resource)
