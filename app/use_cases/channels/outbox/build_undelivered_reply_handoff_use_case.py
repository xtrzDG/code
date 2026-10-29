from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffSummaryCode,
    HandoffUrgency,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.handoffs import CodedHandoffSummary, HandoffCommand
from app.schemas.typings.handoffs.strings import HandoffQuotedText

MAX_QUOTED_REPLY_LENGTH: int = 300


class BuildUndeliveredReplyHandoffUseCase(
    UseCaseContract[OutboundMessageDocument, HandoffCommand | None]
):
    """
    A reply the customer will never get (the platform refused it, or every
    retry failed) becomes a handoff: a colleague takes the conversation
    over and staff are told, in their own language, with the reply that
    did not arrive (the platform's error stays on the outbound message).
    None when it is not such a reply, or staff already own the
    conversation.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        conversation_repo: ConversationRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo

    def run(self, input_data: OutboundMessageDocument) -> HandoffCommand | None:
        if (
            input_data.kind is not OutboundMessageKind.CUSTOMER_REPLY
            or input_data.status is not OutboundMessageStatus.DEAD
            or input_data.conversation_id is None
        ):
            return None

        conversation: ConversationDocument | None = self._conversation_repo.get(
            input_data.business_id, input_data.conversation_id
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if (
            conversation is None
            or business is None
            or conversation.status is ConversationStatus.HANDOFF
        ):
            return None

        return HandoffCommand(
            business_id=input_data.business_id,
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
            reason=HandoffReason.NON_STANDARD_REQUEST,
            summary=build_undelivered_summary(input_data),
            urgency=HandoffUrgency.HIGH,
            source_channel=conversation.channel,
            language=conversation.language or business.default_language,
            is_sandbox=conversation.is_sandbox,
        )


def build_undelivered_summary(message: OutboundMessageDocument) -> CodedHandoffSummary:
    return CodedHandoffSummary(
        code=HandoffSummaryCode.REPLY_UNDELIVERED,
        quoted_text=HandoffQuotedText(str(message.text)[:MAX_QUOTED_REPLY_LENGTH]),
    )
