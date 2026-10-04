"""What customers of a business ask about, as last grouped (Overview card)."""

from app.contracts.repositories.topic_repositories import (
    ConversationTopicsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.conversation_topics import (
    ConversationTopicsQuery,
    ConversationTopicsView,
    ConversationTopicView,
    TopicLanguageView,
)


class GetConversationTopicsUseCase(
    UseCaseContract[ConversationTopicsQuery, ConversationTopicsView]
):
    """
    The topics the nightly grouping stored, for owners and staff: labels
    and counts only (no customer text is kept), so no audit entry. Never
    grouped yet: an empty view in the owner's language.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_topics_repo: ConversationTopicsRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._topics_repo: ConversationTopicsRepoContract = conversation_topics_repo

    def run(self, input_data: ConversationTopicsQuery) -> ConversationTopicsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        stored: ConversationTopicsDocument | None = self._topics_repo.get(business.id)
        if stored is None:
            return ConversationTopicsView(
                business_id=business.id, label_language=business.owner_language
            )

        return ConversationTopicsView(
            business_id=business.id,
            label_language=stored.label_language,
            window_from=stored.window_from,
            window_to=stored.window_to,
            groups=[
                TopicLanguageView(
                    language=group.language,
                    conversation_count=group.conversation_count,
                    topics=[
                        ConversationTopicView(
                            label=topic.label,
                            conversation_count=topic.conversation_count,
                            unanswered_count=topic.unanswered_count,
                        )
                        for topic in group.topics
                    ],
                )
                for group in sorted(
                    stored.groups, key=lambda group: -int(group.conversation_count)
                )
            ],
        )
