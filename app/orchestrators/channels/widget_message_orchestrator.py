from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels import (
    WidgetMessageCommand,
    WidgetReplyInput,
    WidgetReplyView,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage


class WidgetMessageOrchestrator(
    OrchestratorContract[WidgetMessageCommand, WidgetReplyView]
):
    """
    A visitor message in the website chat widget: accept it for the
    business, let the assistant answer through the customer-message
    pipeline, and return the answer to the widget (no text while staff
    handle the conversation).
    """

    def __init__(
        self,
        accept_widget_message: UseCaseContract[WidgetMessageCommand, InboundMessage],
        customer_message_pipeline: CustomerMessagePipelineContract,
        build_widget_reply: UseCaseContract[WidgetReplyInput, WidgetReplyView],
    ) -> None:
        self._accept_widget_message: UseCaseContract[
            WidgetMessageCommand,
            InboundMessage,
        ] = accept_widget_message
        self._customer_message_pipeline: CustomerMessagePipelineContract = (
            customer_message_pipeline
        )
        self._build_widget_reply: UseCaseContract[WidgetReplyInput, WidgetReplyView] = (
            build_widget_reply
        )

    def execute(self, input_data: WidgetMessageCommand) -> WidgetReplyView:
        message: InboundMessage = self._accept_widget_message.run(input_data)
        reply: AssistantReply = self._customer_message_pipeline.start(message)
        return self._build_widget_reply.run(
            WidgetReplyInput(business_id=message.business_id, reply=reply)
        )
