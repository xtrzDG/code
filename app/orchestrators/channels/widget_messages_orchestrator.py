from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.widget import WidgetMessagesQuery, WidgetMessagesView
from app.schemas.dto.channels.widget_streams import WidgetStreamTicketRequest
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket


class WidgetMessagesOrchestrator(
    OrchestratorContract[WidgetMessagesQuery, WidgetMessagesView]
):
    """
    A widget's poll: the answers it has not shown yet, and a fresh ticket
    to the visitor's live stream (the key came in the poll's header), so a
    widget whose stream ticket expired or that came back to the page can
    listen again instead of polling.
    """

    def __init__(
        self,
        get_widget_messages: UseCaseContract[WidgetMessagesQuery, WidgetMessagesView],
        issue_stream_ticket: UseCaseContract[
            WidgetStreamTicketRequest, WidgetStreamTicket
        ],
    ) -> None:
        self._get_widget_messages: UseCaseContract[
            WidgetMessagesQuery, WidgetMessagesView
        ] = get_widget_messages
        self._issue_stream_ticket: UseCaseContract[
            WidgetStreamTicketRequest, WidgetStreamTicket
        ] = issue_stream_ticket

    def execute(self, input_data: WidgetMessagesQuery) -> WidgetMessagesView:
        view: WidgetMessagesView = self._get_widget_messages.run(input_data)
        ticket: WidgetStreamTicket = self._issue_stream_ticket.run(
            WidgetStreamTicketRequest(
                business_id=input_data.business_id,
                session_key=input_data.session_key,
            )
        )
        return view.model_copy(update={"stream_ticket": ticket})
