from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.calendar_commands import (
    SyncResourceCalendarCommand,
)
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges


class SyncResourceCalendarUseCase(
    UseCaseContract[SyncResourceCalendarCommand, ResourceCalendarView]
):
    """
    "Sync now": every source of the resource read at once, each within 2 s
    (a source that does not answer in time keeps its busy times and says
    so), then the calendars as they are.
    """

    def __init__(self, changes: CalendarChanges) -> None:
        self._changes: CalendarChanges = changes

    def run(self, input_data: SyncResourceCalendarCommand) -> ResourceCalendarView:
        resource: ResourceDocument = self._changes.reader.resource(
            input_data.business_id, input_data.resource_id
        )
        return self._changes.synced_view(resource)
