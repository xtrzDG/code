"""
Positions of keyset pages (`page_positions_by`): exactly the rows and order
`page_by` returns, as sort values and storage keys, in memory and on
Postgres, and a walk by positions alone visits the same pages.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.storage_pages import DocumentPagePosition, DocumentPageQuery
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldExclusion,
    DocumentFieldMatch,
    DocumentFilter,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import StoredDocumentKey
from tests.storage.conftest import CollectionFactory
from tests.storage.test_document_pages import (
    BUSINESS,
    CHANNEL,
    IS_SANDBOX,
    LAST_SEEN_AT,
    OCCURRENCE_COUNT,
    conversation,
    feed_query,
    text,
)

pytestmark = pytest.mark.usefixtures("platform_scope")


def question_position(question: UnansweredQuestionDocument) -> DocumentPagePosition:
    return DocumentPagePosition(
        values=(
            DocumentFieldInteger(int(question.occurrence_count)),
            DocumentFieldInteger(int(question.last_seen_at)),
        ),
        document_key=StoredDocumentKey(str(question.id)),
    )


def test_positions_are_the_rows_of_the_page_in_both_directions(
    collections: CollectionFactory,
) -> None:
    questions = collections(UnansweredQuestionDocument, "unanswered_questions")
    business_id = BusinessId()
    for count, seen in ((3, 10), (1, 50), (3, 40), (2, 20), (3, 40), (3, 40)):
        question = UnansweredQuestionDocument(
            business_id=business_id,
            question=UnansweredQuestionText(f"Question {count}/{seen}"),
            language=LanguageTag("en"),
            occurrence_count=QuestionOccurrenceCount(count),
            last_seen_at=Microseconds(seen),
        )
        questions.upsert(str(question.id), question)

    for is_descending in (True, False):
        walked: list[DocumentPagePosition] = []
        position: DocumentPagePosition | None = None
        for _ in range(6):
            query = DocumentPageQuery(
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
            positions = questions.page_positions_by(query)

            assert positions == [
                question_position(question) for question in questions.page_by(query)
            ]
            walked.extend(positions)
            if not positions:
                break
            # The next page starts after the last position alone.
            position = positions[-1]

        assert len(walked) == 6
        assert len({str(found.document_key) for found in walked}) == 6


def test_positions_follow_the_filters_of_the_page(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    stored = [
        conversation(business_id, 30, ChannelKind.TELEGRAM),
        conversation(business_id, 40, ChannelKind.TELEGRAM, is_sandbox=True),
        conversation(business_id, 50),
        conversation(business_id, 50),
        conversation(BusinessId(), 60),
    ]
    for document in stored:
        conversations.upsert(str(document.id), document)

    for query in (
        feed_query(business_id, 10),
        feed_query(business_id, 2, stored[3]),
        feed_query(
            business_id,
            10,
            excluding=(DocumentFieldExclusion(field=IS_SANDBOX, value=text("true")),),
        ),
        feed_query(
            business_id,
            10,
            among=(DocumentFieldAmong(field=CHANNEL, values=(text("telegram"),)),),
        ),
        feed_query(
            business_id, 10, among=(DocumentFieldAmong(field=CHANNEL, values=()),)
        ),
    ):
        assert conversations.page_positions_by(query) == [
            DocumentPagePosition(
                values=(DocumentFieldInteger(int(found.last_message_at)),),
                document_key=StoredDocumentKey(str(found.id)),
            )
            for found in conversations.page_by(query)
        ]
