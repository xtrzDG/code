from app.contracts.calendar_sync import (
    IcalExportFeedRepoContract,
    ResourceCalendarLinkRepoContract,
)
from app.contracts.operations import (
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calendar_sync import (
    BookingSystemKind,
    IntegrationKind,
    IntegrationState,
)
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.domain.calendar_sync import (
    BusySourceStatus,
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.dto.calendar_sync.calendar_commands import BusinessCalendarsQuery
from app.schemas.dto.calendar_sync.integrations import IntegrationList, IntegrationView
from app.use_cases.calendar_sync.integration_states import (
    integration_view,
    resource_summaries,
)


class ListIntegrationsUseCase(UseCaseContract[BusinessCalendarsQuery, IntegrationList]):
    """
    Settings → Integrations: Google Calendar (unavailable when this server
    has no Google credentials; its bookings mirror and the resources it
    blocks), iCal import, iCal export (last read by a calendar) and
    Cal.com, each with how many resources use it, how many need attention
    (their last read failed) and when it last synced; and each resource's
    calendars at a glance for the resources list.
    """

    def __init__(
        self,
        link_repo: ResourceCalendarLinkRepoContract,
        export_feed_repo: IcalExportFeedRepoContract,
        connection_repo: CalendarConnectionRepoContract,
        calendar_client: GoogleCalendarClientContract,
    ) -> None:
        self._link_repo: ResourceCalendarLinkRepoContract = link_repo
        self._export_feed_repo: IcalExportFeedRepoContract = export_feed_repo
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client

    def run(self, input_data: BusinessCalendarsQuery) -> IntegrationList:
        links: list[ResourceCalendarLinkDocument] = self._link_repo.list_by_business(
            input_data.business_id
        )
        return IntegrationList(
            items=[
                self._google(input_data, links),
                integration_view(
                    IntegrationKind.ICAL_IMPORT,
                    [
                        [feed.status for feed in link.ical_imports]
                        for link in links
                        if link.ical_imports
                    ],
                ),
                self._export(links),
                integration_view(
                    IntegrationKind.CAL_COM,
                    [
                        [link.booking_system.status]
                        for link in links
                        if link.booking_system is not None
                        and link.booking_system.kind is BookingSystemKind.CAL_COM
                    ],
                ),
            ],
            resources=resource_summaries(links),
        )

    def _google(
        self,
        input_data: BusinessCalendarsQuery,
        links: list[ResourceCalendarLinkDocument],
    ) -> IntegrationView:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(input_data.business_id)
        )
        statuses: list[list[BusySourceStatus]] = [
            [link.google_status] for link in links if link.google_status is not None
        ]
        summary: IntegrationView = integration_view(
            IntegrationKind.GOOGLE_CALENDAR,
            statuses,
            extra_attention=connection is not None
            and connection.last_sync_error is not None,
            extra_synced_at=None if connection is None else connection.last_synced_at,
        )
        return summary.model_copy(
            update={
                "state": google_state(
                    summary,
                    connection,
                    is_configured=self._calendar_client.is_configured(),
                )
            }
        )

    def _export(self, links: list[ResourceCalendarLinkDocument]) -> IntegrationView:
        feeds: list[IcalExportFeedDocument] = [
            feed
            for link in links
            if link.ical_export_token_hash is not None
            and (feed := self._export_feed_repo.find(link.ical_export_token_hash))
            is not None
        ]
        reads: list[BusySourceStatus] = [
            BusySourceStatus(last_synced_at=feed.last_read_at) for feed in feeds
        ]
        return integration_view(IntegrationKind.ICAL_EXPORT, [[read] for read in reads])


def google_state(
    summary: IntegrationView,
    connection: CalendarConnectionDocument | None,
    is_configured: bool,
) -> IntegrationState:
    """
    Connected: on, or needing attention; not connected: unavailable on a
    server without Google credentials, off, or needing attention when
    resources still name a Google calendar.
    """

    if connection is not None:
        return (
            IntegrationState.ATTENTION
            if summary.state is IntegrationState.ATTENTION
            else IntegrationState.ON
        )
    if int(summary.resource_count) > 0:
        return IntegrationState.ATTENTION
    return IntegrationState.OFF if is_configured else IntegrationState.UNAVAILABLE
