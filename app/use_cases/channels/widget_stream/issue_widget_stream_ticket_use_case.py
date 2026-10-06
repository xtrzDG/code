from typed_time_provider import Microseconds, WallClock

from app.contracts.use_case_contract import UseCaseContract
from app.contracts.widget_streams import WidgetStreamTicketSignerContract
from app.schemas.dto.channels.widget_streams import WidgetStreamTicketRequest
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.utilities.channels.widget_stream_tickets import issue_stream_ticket


class IssueWidgetStreamTicketUseCase(
    UseCaseContract[WidgetStreamTicketRequest, WidgetStreamTicket]
):
    """
    A ticket to the visitor's live stream, for an answer to a request that
    carried the visitor key (never in an address): signed, an hour long,
    naming the visitor one-way. Nothing is read or stored.
    """

    def __init__(
        self,
        ticket_signer: WidgetStreamTicketSignerContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._ticket_signer: WidgetStreamTicketSignerContract = ticket_signer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetStreamTicketRequest) -> WidgetStreamTicket:
        return issue_stream_ticket(
            self._ticket_signer,
            input_data.business_id,
            str(input_data.session_key),
            self._wall_clock.now_unix(),
        )
