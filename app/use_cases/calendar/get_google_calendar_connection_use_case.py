from app.contracts.operations import (
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.dto.calendar import (
    CalendarConnectionStatusQuery,
    CalendarConnectionStatusView,
)


class GetGoogleCalendarConnectionUseCase(
    UseCaseContract[CalendarConnectionStatusQuery, CalendarConnectionStatusView]
):
    """
    The Google Calendar connection of a business as the cabinet shows it:
    whether this server can connect calendars at all, whether one is
    connected, which calendar, since when, and how the last sync went.
    Tokens never leave the server.
    """

    def __init__(
        self,
        connection_repo: CalendarConnectionRepoContract,
        calendar_client: GoogleCalendarClientContract,
    ) -> None:
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client

    def run(
        self,
        input_data: CalendarConnectionStatusQuery,
    ) -> CalendarConnectionStatusView:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(input_data.business_id)
        )
        is_configured: bool = self._calendar_client.is_configured()
        if connection is None:
            return CalendarConnectionStatusView(
                business_id=input_data.business_id,
                is_configured=is_configured,
                is_connected=False,
            )

        return CalendarConnectionStatusView(
            business_id=input_data.business_id,
            is_configured=is_configured,
            is_connected=True,
            calendar_id=connection.calendar_id,
            calendar_name=connection.calendar_name,
            connected_at=connection.created_at,
            last_synced_at=connection.last_synced_at,
            last_sync_error=connection.last_sync_error,
            last_sync_error_at=connection.last_sync_error_at,
        )
