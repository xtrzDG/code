from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.widget import WidgetMessageCommand
from app.schemas.dto.channels.widget_turns import WidgetMessageAcceptedView
from app.schemas.dto.conversations import InboundMessage


class WidgetMessageOrchestrator(
    OrchestratorContract[WidgetMessageCommand, WidgetMessageAcceptedView]
):
    """
    A visitor message in the website chat widget: accept it for the
    business (limits, the chat switched on, the assistant live), then put
    it into the inbox for a worker to answer. The request returns at once
    (202); the widget shows typing until its polling brings the answer.
    """

    def __init__(
        self,
        accept_widget_message: UseCaseContract[WidgetMessageCommand, InboundMessage],
        queue_widget_message: UseCaseContract[
            InboundMessage, WidgetMessageAcceptedView
        ],
    ) -> None:
        self._accept_widget_message: UseCaseContract[
            WidgetMessageCommand,
            InboundMessage,
        ] = accept_widget_message
        self._queue_widget_message: UseCaseContract[
            InboundMessage, WidgetMessageAcceptedView
        ] = queue_widget_message

    def execute(self, input_data: WidgetMessageCommand) -> WidgetMessageAcceptedView:
        accepted: InboundMessage = self._accept_widget_message.run(input_data)
        return self._queue_widget_message.run(accepted)
