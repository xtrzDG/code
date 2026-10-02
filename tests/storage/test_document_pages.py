"""Keyset pages of the document store: the same pages in memory and on Postgres."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.storage_pages import DocumentPagePosition, DocumentPageQuery
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldExclusion,
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText, StoredDocumentKey
from tests.storage.conftest import CollectionFactory
from tests.storage.test_document_lookups import message

pytestmark = pytest.mark.usefixtures("platform_scope")

BUSINESS = DocumentFieldPath("business_id")
LAST_MESSAGE_AT = DocumentFieldPath("last_message_at")
CREATED_AT = DocumentFieldPath("created_at")
CHANNEL = DocumentFieldPath("channel")
LANGUAGE = DocumentFieldPath("language")
IS_SANDBOX = DocumentFieldPath("is_sandbox")
STATUS = DocumentFieldPath("status")
CONVERSATION = DocumentFieldPath("conversation_id")
OCCURRENCE_COUNT = DocumentFieldPath("occurrence_count")
LAST_SEEN_AT = DocumentFieldPath("last_seen_at")


def text(value: str) -> DocumentFieldText:
    return DocumentFieldText(value)


def conversation(
    business_id: BusinessId,
    last_message_at: int,
    channel: ChannelKind = ChannelKind.WHATSAPP,
    is_sandbox: bool = False,
    language: str | None = None,
) -> ConversationDocument:
    return ConversationDocument(
        business_id=business_id,
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=channel,
        channel_user_id=ChannelUserId("user"),
        language=None if language is None else LanguageTag(language),
        is_sandbox=is_sandbox,
        last_message_at=Microseconds(last_message_at),
        created_at=Microseconds(last_message_at - 5),
        updated_at=Microseconds(last_message_at),
    )


def feed_query(
    business_id: BusinessId,
    limit: int,
    after: ConversationDocument | None = None,
    **where: object,
) -> DocumentPageQuery:
    return DocumentPageQuery(
        where=DocumentFilter.model_validate(
            {
                "matches": (
                    DocumentFieldMatch(field=BUSINESS, value=text(str(business_id))),
                ),
                **where,
            }
        ),
        sort_fields=(LAST_MESSAGE_AT,),
        after=(
            None
            if after is None
            else DocumentPagePosition(
                values=(DocumentFieldInteger(int(after.last_message_at)),),
                document_key=StoredDocumentKey(str(after.id)),
            )
        ),
        limit=DocumentQueryLimit(limit),
    )


def test_pages_walk_the_feed_newest_first_with_ties_by_key(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    stored = [conversation(business_id, at) for at in (50, 20, 20, 20, 90, 10)]
    for document in [*stored, conversation(BusinessId(), 70)]:
        conversations.upsert(str(document.id), document)
    expected = sorted(
        stored, key=lambda c: (int(c.last_message_at), str(c.id)), reverse=True
    )

    walked: list[ConversationDocument] = []
    after: ConversationDocument | None = None
    while True:
        page = conversations.page_by(feed_query(business_id, 2, after))
        walked.extend(page)
        if len(page) < 2:
            break
        after = page[-1]

    assert [c.id for c in walked] == [c.id for c in expected]


def test_filters_narrow_a_page(collections: CollectionFactory) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    telegram = conversation(business_id, 30, ChannelKind.TELEGRAM, language="ka")
    sandbox = conversation(business_id, 40, ChannelKind.TELEGRAM, is_sandbox=True)
    whatsapp = conversation(business_id, 50, language="en")
    for document in (telegram, sandbox, whatsapp):
        conversations.upsert(str(document.id), document)

    real = conversations.page_by(
        feed_query(
            business_id,
            10,
            excluding=(DocumentFieldExclusion(field=IS_SANDBOX, value=text("true")),),
        )
    )
    telegram_only = conversations.page_by(
        feed_query(
            business_id,
            10,
            among=(DocumentFieldAmong(field=CHANNEL, values=(text("telegram"),)),),
        )
    )
    not_english = conversations.page_by(
        feed_query(
            business_id,
            10,
            excluding=(DocumentFieldExclusion(field=LANGUAGE, value=text("en")),),
        )
    )
    nothing = conversations.page_by(
        feed_query(
            business_id, 10, among=(DocumentFieldAmong(field=CHANNEL, values=()),)
        )
    )
    recent = conversations.page_by(
        feed_query(
            business_id,
            10,
            ranges=(
                DocumentFieldRange(
                    field=LAST_MESSAGE_AT, lower=DocumentFieldInteger(35)
                ),
                DocumentFieldRange(field=CREATED_AT, upper=DocumentFieldInteger(40)),
            ),
        )
    )

    assert [c.id for c in real] == [whatsapp.id, telegram.id]
    assert [c.id for c in telegram_only] == [sandbox.id, telegram.id]
    # A missing language (None) is not "en": exclusions keep it.
    assert [c.id for c in not_english] == [sandbox.id, telegram.id]
    assert nothing == []
    assert [c.id for c in recent] == [sandbox.id]


def test_ascending_pages_and_several_sort_fields(
    collections: CollectionFactory,
) -> None:
    questions = collections(UnansweredQuestionDocument, "unanswered_questions")
    business_id = BusinessId()
    stored = [
        UnansweredQuestionDocument(
            business_id=business_id,
            question=UnansweredQuestionText(f"Question {count}/{seen}"),
            language=LanguageTag("en"),
            occurrence_count=QuestionOccurrenceCount(count),
            last_seen_at=Microseconds(seen),
        )
        for count, seen in ((3, 10), (1, 50), (3, 40), (2, 20), (3, 40))
    ]
    for document in stored:
        questions.upsert(str(document.id), document)

    def rank(question: UnansweredQuestionDocument) -> tuple[int, int, str]:
        return (
            int(question.occurrence_count),
            int(question.last_seen_at),
            str(question.id),
        )

    for is_descending in (True, False):
        expected = sorted(stored, key=rank, reverse=is_descending)
        walked: list[UnansweredQuestionDocument] = []
        position: DocumentPagePosition | None = None
        for _ in range(len(stored)):
            page = questions.page_by(
                DocumentPageQuery(
                    where=DocumentFilter(
                        matches=(
                            DocumentFieldMatch(
                                field=BUSINESS, value=text(str(business_id))
                            ),
                        )
                    ),
                    sort_fields=(OCCURRENCE_COUNT, LAST_SEEN_AT),
                    is_descending=is_descending,
                    after=position,
                    limit=DocumentQueryLimit(2),
                )
            )
            walked.extend(page)
            if not page:
                break
            last = page[-1]
            position = DocumentPagePosition(
                values=(
                    DocumentFieldInteger(int(last.occurrence_count)),
                    DocumentFieldInteger(int(last.last_seen_at)),
                ),
                document_key=StoredDocumentKey(str(last.id)),
            )

        assert [q.id for q in walked] == [q.id for q in expected]


def test_pages_of_messages_by_conversation(collections: CollectionFactory) -> None:
    messages = collections(MessageDocument, "messages")
    conversation_id = ConversationId()
    stored = [message(conversation_id, at) for at in (10, 30, 20)]
    for document in [*stored, message(ConversationId(), 25)]:
        messages.upsert(str(document.id), document)

    newest = messages.page_by(
        DocumentPageQuery(
            where=DocumentFilter(
                matches=(
                    DocumentFieldMatch(
                        field=CONVERSATION, value=text(str(conversation_id))
                    ),
                )
            ),
            sort_fields=(CREATED_AT,),
            limit=DocumentQueryLimit(2),
        )
    )

    assert [m.id for m in newest] == [stored[1].id, stored[2].id]


@pytest.mark.parametrize(
    "query",
    ["sort by a text field", "undeclared filter", "exclusion of a list field"],
)
def test_pages_refuse_undeclared_fields(
    collections: CollectionFactory, query: str
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    with pytest.raises(UndeclaredLookupFieldError, match="lookup field"):
        if query == "sort by a text field":
            conversations.page_by(
                DocumentPageQuery(sort_fields=(STATUS,), limit=DocumentQueryLimit(1))
            )
        elif query == "undeclared filter":
            conversations.page_by(
                feed_query(
                    BusinessId(),
                    1,
                    excluding=(
                        DocumentFieldExclusion(
                            field=DocumentFieldPath("rating"), value=text("good")
                        ),
                    ),
                )
            )
        else:
            collections(MessageDocument, "messages").page_by(
                DocumentPageQuery(
                    where=DocumentFilter(
                        excluding=(
                            DocumentFieldExclusion(
                                field=DocumentFieldPath("tool_calls[].is_error"),
                                value=text("true"),
                            ),
                        )
                    ),
                    sort_fields=(CREATED_AT,),
                    limit=DocumentQueryLimit(1),
                )
            )


def test_a_page_query_checks_its_shape() -> None:
    with pytest.raises(ValueError, match="1 to 3"):
        DocumentPageQuery(sort_fields=(), limit=DocumentQueryLimit(1))
    with pytest.raises(ValueError, match="one value per sort field"):
        DocumentPageQuery(
            sort_fields=(CREATED_AT,),
            after=DocumentPagePosition(values=(), document_key=StoredDocumentKey("x")),
            limit=DocumentQueryLimit(1),
        )
