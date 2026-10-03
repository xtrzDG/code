from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundAnswer


class RecallInboundReplyUseCase(
    UseCaseContract[InboundEventDocument, InboundAnswer | None]
):
    """
    The reply an earlier processing of the event already stored (it ended
    between storing the reply and queuing it): that reply is sent, the
    model is not asked again. None when no reply was stored.
    """

    def __init__(self, message_repo: MessageRepoContract) -> None:
        self._message_repo: MessageRepoContract = message_repo

    def run(self, input_data: InboundEventDocument) -> InboundAnswer | None:
        if input_data.business_id is None:
            return None

        stored: MessageDocument | None = self._message_repo.get(
            input_data.business_id, input_data.reply_message_id
        )
        if stored is None:
            return None

        return InboundAnswer(
            event=input_data,
            conversation_id=stored.conversation_id,
            text=stored.text,
        )
