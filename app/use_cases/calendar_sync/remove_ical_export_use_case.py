from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.calendar_commands import IcalExportCommand
from app.schemas.typings.calendar_sync.constrained_strings import IcalExportTokenHash
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges


class RemoveIcalExportUseCase(UseCaseContract[IcalExportCommand, None]):
    """
    Owners switch the resource's export address off: it answers 404 from
    now on (calendars that imported it stop seeing its busy times). Audited.
    """

    def __init__(self, changes: CalendarChanges) -> None:
        self._changes: CalendarChanges = changes

    def run(self, input_data: IcalExportCommand) -> None:
        reader = self._changes.reader
        resource: ResourceDocument = reader.resource(
            input_data.business_id, input_data.resource_id
        )
        now: Microseconds = reader.wall_clock.now_unix()
        removed: list[IcalExportTokenHash] = []

        def switch_off(
            link: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument:
            removed.clear()
            if link.ical_export_token_hash is not None:
                removed.append(link.ical_export_token_hash)
            link.ical_export_token_hash = None
            link.ical_export_created_at = None
            link.updated_at = now
            return link

        self._changes.change(resource, switch_off, now)
        for token_hash in removed:
            reader.export_feed_repo.remove(resource.business_id, token_hash)
        if removed:
            self._changes.audit(resource, input_data.actor_id, AuditAction.DELETE, now)
