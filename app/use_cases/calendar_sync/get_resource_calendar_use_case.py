from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calendar_sync.calendar_commands import ResourceCalendarQuery
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.use_cases.calendar_sync.resource_calendar_reader import (
    ResourceCalendarReader,
)


class GetResourceCalendarUseCase(
    UseCaseContract[ResourceCalendarQuery, ResourceCalendarView]
):
    """
    The calendars of one resource for owners and staff: the Google calendar
    that blocks it, the feeds it imports (their hosts), its booking system
    (never its key), whether it has an export address, how each source
    synced, and the next busy times they reported.
    """

    def __init__(self, reader: ResourceCalendarReader) -> None:
        self._reader: ResourceCalendarReader = reader

    def run(self, input_data: ResourceCalendarQuery) -> ResourceCalendarView:
        return self._reader.view(input_data.business_id, input_data.resource_id)
