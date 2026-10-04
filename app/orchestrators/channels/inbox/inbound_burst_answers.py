from typed_time_provider import Microseconds

from app.contracts.conversation_flow import CustomerMessagePipelineContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim
from app.schemas.dto.inbound_bursts import InboundBurst
from app.schemas.dto.media_requests import InboundMediaRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.booleans import IsReplyDeferred


class InboundBurstAnswers:
    """
    The turns of one burst of a customer's messages, oldest first, through
    the customer-message pipeline (one customer at a time). Every message is
    stored in its conversation; only the last is answered by the model, and
    its turn reads the earlier ones (they come before it in the transcript),
    so three quick messages get one reply. A platform signal among them
    (STOP, a visit rating) is still answered on its own. Voice notes, photos
    and places are read first (downloaded, stored, transcribed). A reply an
    earlier attempt already stored is reused instead of asking again.
    """

    def __init__(
        self,
        recall_inbound_reply: UseCaseContract[
            InboundEventDocument, InboundAnswer | None
        ],
        customer_message_pipeline: CustomerMessagePipelineContract,
        read_inbound_attachments: OrchestratorContract[
            InboundMediaRequest, InboundMessage
        ],
    ) -> None:
        self._recall_inbound_reply: UseCaseContract[
            InboundEventDocument, InboundAnswer | None
        ] = recall_inbound_reply
        self._customer_message_pipeline: CustomerMessagePipelineContract = (
            customer_message_pipeline
        )
        self._read_inbound_attachments: OrchestratorContract[
            InboundMediaRequest, InboundMessage
        ] = read_inbound_attachments

    def answer(self, burst: InboundBurst) -> list[InboundAnswer]:
        """One answer per message of the burst, in its order."""

        waiting_since: Microseconds = burst.claims[0].event.created_at
        last_index: int = len(burst.claims) - 1
        return [
            self._answer_one(claim, waiting_since, IsReplyDeferred(index < last_index))
            for index, claim in enumerate(burst.claims)
        ]

    def _answer_one(
        self,
        claim: InboundEventClaim,
        waiting_since: Microseconds,
        is_reply_deferred: IsReplyDeferred,
    ) -> InboundAnswer:
        recalled: InboundAnswer | None = self._recall_inbound_reply.run(claim.event)
        if recalled is not None:
            return recalled

        if claim.message is None:
            raise ValidationFailedError("The inbox event holds no customer message.")

        message: InboundMessage = claim.message
        if claim.event.customer_message and claim.event.customer_message.attachments:
            message = self._read_inbound_attachments.execute(
                InboundMediaRequest(
                    event=claim.event,
                    message=message,
                    is_final_attempt=claim.is_final_attempt,
                )
            )

        reply: AssistantReply = self._customer_message_pipeline.start(
            message.model_copy(
                update={
                    "waiting_since": waiting_since,
                    "is_reply_deferred": is_reply_deferred,
                }
            )
        )
        return InboundAnswer(
            event=claim.event,
            conversation_id=reply.conversation_id,
            text=reply.text,
            is_handed_off=reply.is_handed_off,
        )
