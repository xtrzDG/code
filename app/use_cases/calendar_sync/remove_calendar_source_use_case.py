from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.calendar_commands import (
    RemoveCalendarSourceCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges


class RemoveCalendarSourceUseCase(UseCaseContract[RemoveCalendarSourceCommand, None]):
    """
    Owners stop a source blocking a resource: its Google calendar, one
    imported feed, or its booking system. Its busy times are forgotten at
    once (a read still running cannot bring them back); a resource with no
    source left is not read any more. Audited.
    """

    def __init__(self, changes: CalendarChanges) -> None:
        self._changes: CalendarChanges = changes

    def run(self, input_data: RemoveCalendarSourceCommand) -> None:
        reader = self._changes.reader
        resource: ResourceDocument = reader.resource(
            input_data.business_id, input_data.resource_id
        )
        now: Microseconds = reader.wall_clock.now_unix()
        if input_data.source is BusyTimeSource.GOOGLE:
            resource.external_calendar_id = None
            resource.updated_at = now
            reader.resource_repo.save(resource)

        def remove(link: ResourceCalendarLinkDocument) -> ResourceCalendarLinkDocument:
            if input_data.source is BusyTimeSource.GOOGLE:
                link.google_status = None
            elif input_data.source is BusyTimeSource.BOOKING_SYSTEM:
                link.booking_system = None
            else:
                kept = [
                    feed
                    for feed in link.ical_imports
                    if feed.feed_id != input_data.feed_id
                ]
                if len(kept) == len(link.ical_imports):
                    raise NotFoundError("This calendar is not imported here.")
                link.ical_imports = kept
            if not (link.google_status or link.ical_imports or link.booking_system):
                link.next_sync_at = None
            link.updated_at = now
            return link

        self._changes.change(resource, remove, now)
        self._changes.forget(resource, input_data.source, input_data.feed_id)
        self._changes.audit(resource, input_data.actor_id, AuditAction.DELETE, now)
