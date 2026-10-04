"""What customers ask about: the topics document and the grouping's reads."""

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.topic_repositories import (
    ConversationTopicsRepoContract,
    TopicInputRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    AUTHOR_FIELD,
    CONVERSATION_ID_FIELD,
)
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    of_business,
    time_range,
    without_sandbox,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.value.value_keys import conversation_topics_id_of


class ConversationTopicsRepository(
    BusinessScopedRepository[ConversationTopicsDocument],
    ConversationTopicsRepoContract,
):
    """One topics document per business, keyed by the derived id."""

    def get(self, business_id: BusinessId) -> ConversationTopicsDocument | None:
        return self._load(business_id, str(conversation_topics_id_of(business_id)))

    def save(self, topics: ConversationTopicsDocument) -> None:
        self._store(str(topics.id), topics)


class TopicInputRepository(TopicInputRepoContract):
    """
    Keyset reads over indexed columns: the conversations a period started
    (`conversations_doc_created_at_idx`) and, per conversation, its first
    customer message (`messages_doc_conversation_idx`, one probe each).
    """

    def __init__(
        self,
        conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ],
        message_collection: DocumentCollectionAdapterContract[MessageDocument],
    ) -> None:
        self._conversations: DocumentCollectionAdapterContract[ConversationDocument] = (
            conversation_collection
        )
        self._messages: DocumentCollectionAdapterContract[MessageDocument] = (
            message_collection
        )

    def list_started(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        return self._conversations.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(of_business(business_id),),
                    excluding=(without_sandbox(),),
                    ranges=(time_range(CREATED_AT_FIELD, start, end),),
                ),
                sort_fields=(CREATED_AT_FIELD,),
                limit=limit,
            )
        )

    def find_first_customer_message(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> MessageDocument | None:
        first: list[MessageDocument] = self._messages.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(
                        of_business(business_id),
                        field_equals(CONVERSATION_ID_FIELD, conversation_id),
                        field_equals(AUTHOR_FIELD, MessageAuthor.CUSTOMER),
                    )
                ),
                sort_fields=(CREATED_AT_FIELD,),
                is_descending=False,
                limit=DocumentQueryLimit(1),
            )
        )
        return first[0] if first else None
