from app.contracts.repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed import (
    ConversationListQuery,
    ConversationSummaryView,
    ConversationViewSource,
)


class ListConversationsUseCase(
    UseCaseContract[ConversationListQuery, list[ConversationSummaryView]]
):
    """
    Conversation feed of a business for owners and staff (concept section 8,
    /conversations), newest first, optionally of one channel. Sandbox
    conversations (owner test chat, autotests) appear only on request.
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

    def run(self, input_data: ConversationListQuery) -> list[ConversationSummaryView]:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        summaries: list[ConversationSummaryView] = []
        for conversation in self._conversation_repo.list_by_business(business.id):
            if conversation.is_sandbox and not input_data.include_sandbox:
                continue

            if input_data.channel is not None and conversation.channel is not (
                input_data.channel
            ):
                continue

            summaries.append(
                self._summary_transformer.transform(
                    ConversationViewSource(
                        conversation=conversation,
                        contact=self._contact_repo.get(
                            business.id, conversation.contact_id
                        ),
                        messages=self._message_repo.list_by_conversation(
                            business.id, conversation.id
                        ),
                    )
                )
            )

        return summaries
