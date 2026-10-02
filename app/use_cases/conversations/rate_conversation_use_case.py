from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_actions import (
    RateConversationCommand,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationSummaryView,
    ConversationViewSource,
)
from app.schemas.exceptions.application_errors import NotFoundError


class RateConversationUseCase(
    UseCaseContract[RateConversationCommand, ConversationSummaryView]
):
    """
    Owner or staff marks how the assistant handled a conversation, good or
    bad (concept section 8, the conversation card), for the weekly quality
    review (section 11). Who rated and when is kept; null clears it.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ] = summary_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RateConversationCommand) -> ConversationSummaryView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        conversation: ConversationDocument | None = self._conversation_repo.get(
            business.id, input_data.conversation_id
        )
        if conversation is None:
            raise NotFoundError(
                f"Conversation {input_data.conversation_id} was not found."
            )

        now: Microseconds = self._wall_clock.now_unix()
        conversation.rating = input_data.rating
        conversation.rated_by = (
            None if input_data.rating is None else input_data.user_id
        )
        conversation.rated_at = None if input_data.rating is None else now
        conversation.updated_at = now
        self._conversation_repo.save(conversation)
        return self._summary_transformer.transform(
            ConversationViewSource(
                conversation=conversation,
                contact=self._contact_repo.get(business.id, conversation.contact_id),
                messages=self._message_repo.list_by_conversation(
                    business.id, conversation.id
                ),
            )
        )
