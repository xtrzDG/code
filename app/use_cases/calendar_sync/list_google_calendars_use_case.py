from app.contracts.calendar_sync import BusyTimeSyncFacilitatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.calendar_sync.busy_reads import GoogleCalendarList
from app.schemas.dto.calendar_sync.calendar_commands import BusinessCalendarsQuery
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds

LIST_SECONDS: BusyTimeFetchSeconds = BusyTimeFetchSeconds(5.0)


class ListGoogleCalendarsUseCase(
    UseCaseContract[BusinessCalendarsQuery, GoogleCalendarList]
):
    """
    The calendars of the business's connected Google account that a
    resource can be linked to (those whose busy times it may see). Not
    readable, with the reason, when Google Calendar is not connected or was
    connected before calendars were read (connect it again).
    """

    def __init__(self, busy_time_sync: BusyTimeSyncFacilitatorContract) -> None:
        self._busy_time_sync: BusyTimeSyncFacilitatorContract = busy_time_sync

    def run(self, input_data: BusinessCalendarsQuery) -> GoogleCalendarList:
        return self._busy_time_sync.list_google_calendars(
            input_data.business_id, LIST_SECONDS
        )
