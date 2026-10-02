from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.widget import (
    WidgetMessageCommand,
    WidgetReplyInput,
    WidgetReplyView,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.deliveries.inbound_failures import (
    describe_inbound_error,
    is_inbound_refusal,
)


class WidgetMessageOrchestrator(
    OrchestratorContract[WidgetMessageCommand, WidgetReplyView]
):
    """
    A visitor message in the website chat widget: accept it for the
    business, write it into the inbox (held by this request), let the
    assistant answer through the customer-message pipeline and return the
    answer to the widget (no text while staff handle the conversation).

    The visitor waits for the answer as before, but the message is never
    lost: when the server dies mid-turn, the inbox's job answers it once
    this request's lease ends and the widget's polling shows the reply. A
    refusal (the assistant is not live) closes the event as FAILED.
    """

    def __init__(
        self,
        accept_widget_message: UseCaseContract[WidgetMessageCommand, InboundMessage],
        open_widget_event: UseCaseContract[InboundMessage, InboundEventClaim],
        customer_message_pipeline: CustomerMessagePipelineContract,
        finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ],
        release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ],
        build_widget_reply: UseCaseContract[WidgetReplyInput, WidgetReplyView],
    ) -> None:
        self._accept_widget_message: UseCaseContract[
            WidgetMessageCommand,
            InboundMessage,
        ] = accept_widget_message
        self._open_widget_event: UseCaseContract[InboundMessage, InboundEventClaim] = (
            open_widget_event
        )
        self._customer_message_pipeline: CustomerMessagePipelineContract = (
            customer_message_pipeline
        )
        self._finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ] = finish_inbound_event
        self._release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ] = release_inbound_event
        self._build_widget_reply: UseCaseContract[WidgetReplyInput, WidgetReplyView] = (
            build_widget_reply
        )

    def execute(self, input_data: WidgetMessageCommand) -> WidgetReplyView:
        accepted: InboundMessage = self._accept_widget_message.run(input_data)
        claim: InboundEventClaim = self._open_widget_event.run(accepted)
        if claim.message is None:
            raise ValidationFailedError("The widget message could not be stored.")

        try:
            reply: AssistantReply = self._customer_message_pipeline.start(
                claim.message
            )
        except Exception as error:
            if is_inbound_refusal(error):
                self._release_inbound_event.run(
                    InboundFailure(
                        event_id=claim.event.id,
                        business_id=claim.event.business_id,
                        error=describe_inbound_error(error),
                        is_final=True,
                    )
                )

            # Otherwise the event stays held: its job answers it when this
            # request's lease ends.
            raise

        self._finish_inbound_event.run(
            InboundAnswer(
                event=claim.event,
                conversation_id=reply.conversation_id,
                text=reply.text,
                is_handed_off=reply.is_handed_off,
            )
        )
        return self._build_widget_reply.run(
            WidgetReplyInput(business_id=accepted.business_id, reply=reply)
        )
