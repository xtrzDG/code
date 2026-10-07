from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.widget import WidgetMessageCommand
from app.schemas.dto.channels.widget_streams import WidgetStreamTicketRequest
from app.schemas.dto.channels.widget_turns import WidgetMessageAcceptedView
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket


class WidgetMessageOrchestrator(
    OrchestratorContract[WidgetMessageCommand, WidgetMessageAcceptedView]
):
    """
    A visitor message in the website chat widget: accept it for the
    business (limits, the chat switched on, the assistant live), then put
    it into the inbox for a worker to answer. The request returns at once
    (202) with a ticket to the visitor's live stream (the key came in the
    message's body), which says when the answer is ready; a widget without
    EventSource polls for it.
    """

    def __init__(
        self,
        accept_widget_message: UseCaseContract[WidgetMessageCommand, InboundMessage],
        queue_widget_message: UseCaseContract[
            InboundMessage, WidgetMessageAcceptedView
        ],
        issue_stream_ticket: UseCaseContract[
            WidgetStreamTicketRequest, WidgetStreamTicket
        ],
    ) -> None:
        self._accept_widget_message: UseCaseContract[
            WidgetMessageCommand,
            InboundMessage,
        ] = accept_widget_message
        self._queue_widget_message: UseCaseContract[
            InboundMessage, WidgetMessageAcceptedView
        ] = queue_widget_message
        self._issue_stream_ticket: UseCaseContract[
            WidgetStreamTicketRequest, WidgetStreamTicket
        ] = issue_stream_ticket

    def execute(self, input_data: WidgetMessageCommand) -> WidgetMessageAcceptedView:
        accepted: InboundMessage = self._accept_widget_message.run(input_data)
        queued: WidgetMessageAcceptedView = self._queue_widget_message.run(accepted)
        ticket: WidgetStreamTicket = self._issue_stream_ticket.run(
            WidgetStreamTicketRequest(
                business_id=input_data.business_id,
                session_key=input_data.request.session_key,
            )
        )
        return queued.model_copy(update={"stream_ticket": ticket})
