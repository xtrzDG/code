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
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.value.topic_labels import resolve_topic_label


class GetConversationTopicsUseCase(
    UseCaseContract[ConversationTopicsQuery, ConversationTopicsView]
):
    """
    The topics the nightly grouping stored, for owners and staff, labelled
    in the language the member reads the cabinet in (`language`, else the
    owner's): each topic's label in that language, else in English, else in
    the owner's; the catch-all of other questions as OTHER. Labels and
    counts only (no customer text is kept), so no audit entry. Never
    grouped yet: an empty view.
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
        language: LanguageTag = input_data.language or business.owner_language
        stored: ConversationTopicsDocument | None = self._topics_repo.get(business.id)
        if stored is None:
            return ConversationTopicsView(
                business_id=business.id, label_language=language
            )

        return ConversationTopicsView(
            business_id=business.id,
            label_language=language,
            window_from=stored.window_from,
            window_to=stored.window_to,
            groups=[
                TopicLanguageView(
                    language=group.language,
                    conversation_count=group.conversation_count,
                    topics=[
                        ConversationTopicView(
                            label=resolve_topic_label(
                                topic, language, stored.label_language
                            ),
                            kind=topic.kind,
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
