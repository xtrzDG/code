"""`latest_by`: the newest document of each group, on every storage."""

import pytest
from typed_time_provider import Microseconds

from app.repositories.conversation_repositories import MessageRepository
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.storage_pages import DocumentLatestQuery
from app.schemas.dto.storage_queries import DocumentFieldAmong, DocumentFilter
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

CONVERSATION = DocumentFieldPath("conversation_id")
CREATED_AT = DocumentFieldPath("created_at")
AUTHOR = DocumentFieldPath("author")


def message(
    business_id: BusinessId,
    conversation_id: ConversationId,
    at: int,
    author: MessageAuthor = MessageAuthor.CUSTOMER,
) -> MessageDocument:
    return MessageDocument(
        conversation_id=conversation_id,
        business_id=business_id,
        direction=MessageDirection.INBOUND,
        author=author,
        text=MessageText(f"{author.value} at {at}"),
        created_at=Microseconds(at),
        updated_at=Microseconds(at),
    )


def test_each_group_gets_its_newest_document_in_group_order(
    collections: CollectionFactory,
) -> None:
    messages = collections(MessageDocument, "messages")
    repository = MessageRepository(messages)
    business_id = BusinessId()
    first, second, silent = ConversationId(), ConversationId(), ConversationId()
    stored = [
        message(business_id, first, 10),
        message(business_id, first, 30, MessageAuthor.ASSISTANT),
        message(business_id, first, 40, MessageAuthor.SYSTEM),
        message(business_id, second, 20),
        # A tie: the later write wins.
        message(business_id, second, 50),
        message(business_id, second, 50, MessageAuthor.STAFF),
        message(BusinessId(), silent, 99),
    ]
    messages.upsert_many([(str(document.id), document) for document in stored])

    latest = repository.find_latest_written(business_id, [second, silent, first])
    everything = messages.latest_by(
        DocumentLatestQuery(
            group_field=CONVERSATION,
            groups=(DocumentFieldText(str(second)), DocumentFieldText(str(first))),
            sort_field=CREATED_AT,
        )
    )

    assert list(latest) == [second, first]
    assert latest[second].id == stored[5].id
    assert latest[first].id == stored[1].id
    assert [document.id for document in everything] == [stored[5].id, stored[2].id]
    assert repository.find_latest_written(business_id, []) == {}


@pytest.mark.parametrize(
    "query",
    [
        DocumentLatestQuery(group_field=AUTHOR, groups=(), sort_field=CREATED_AT),
        DocumentLatestQuery(group_field=CONVERSATION, groups=(), sort_field=AUTHOR),
        DocumentLatestQuery(
            where=DocumentFilter(
                among=(DocumentFieldAmong(field=DocumentFieldPath("text"), values=()),)
            ),
            group_field=CONVERSATION,
            groups=(),
            sort_field=CREATED_AT,
        ),
    ],
    ids=["group by a filter field", "text sort field", "undeclared filter"],
)
def test_latest_refuses_fields_without_their_index(
    collections: CollectionFactory, query: DocumentLatestQuery
) -> None:
    messages = collections(MessageDocument, "messages")

    with pytest.raises(UndeclaredLookupFieldError, match="lookup field"):
        messages.latest_by(query)


def test_no_groups_read_nothing(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")

    assert (
        conversations.latest_by(
            DocumentLatestQuery(
                group_field=DocumentFieldPath("contact_id"),
                groups=(),
                sort_field=DocumentFieldPath("last_message_at"),
            )
        )
        == []
    )
