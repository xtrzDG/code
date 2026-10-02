from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.channels.inbox.inbound_event_orchestrator import (
    InboundEventOrchestrator,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import ValidationFailedError


class ProcessInboundMessageOrchestrator(InboundEventOrchestrator):
    """
    `process_inbound_message`: answer a customer message from the inbox in
    the worker (concept section 1, path of a message). The assistant's turn
    runs through the customer-message pipeline (one customer's messages one
    at a time); its reply goes into the outbox. When an earlier attempt
    already stored the reply, that reply is queued instead of asking the
    model again.
    """

    def __init__(
        self,
        claim_inbound_event: UseCaseContract[QueuedJobInput, InboundEventClaim | None],
        recall_inbound_reply: UseCaseContract[
            InboundEventDocument, InboundAnswer | None
        ],
        customer_message_pipeline: CustomerMessagePipelineContract,
        finish_inbound_event: UseCaseContract[
            InboundAnswer, InboundEventDocument | None
        ],
        release_inbound_event: UseCaseContract[
            InboundFailure, InboundEventDocument | None
        ],
    ) -> None:
        super().__init__(
            claim_inbound_event, finish_inbound_event, release_inbound_event
        )
        self._recall_inbound_reply: UseCaseContract[
            InboundEventDocument, InboundAnswer | None
        ] = recall_inbound_reply
        self._customer_message_pipeline: CustomerMessagePipelineContract = (
            customer_message_pipeline
        )

    def _process(self, claim: InboundEventClaim) -> InboundAnswer:
        recalled: InboundAnswer | None = self._recall_inbound_reply.run(claim.event)
        if recalled is not None:
            return recalled

        if claim.message is None:
            raise ValidationFailedError("The inbox event holds no customer message.")

        reply: AssistantReply = self._customer_message_pipeline.start(claim.message)
        return InboundAnswer(
            event=claim.event,
            conversation_id=reply.conversation_id,
            text=reply.text,
            is_handed_off=reply.is_handed_off,
        )
