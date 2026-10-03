"""
"Field is missing" conditions of the document store: absent and null are
the same, in memory and on Postgres, for pages and counts; only text lookup
fields qualify, and only next to a condition an index selects by.
"""

import pytest

from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId
from tests.storage.conftest import CollectionFactory
from tests.storage.test_document_pages import (
    LANGUAGE,
    LAST_MESSAGE_AT,
    conversation,
    feed_query,
    text,
)

pytestmark = pytest.mark.usefixtures("platform_scope")

ASSIGNEE = DocumentFieldPath("assignee_user_id")
AWAITS_TEAM = DocumentFieldPath("awaits_team")


def test_missing_fields_narrow_pages_and_counts(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    assigned = conversation(business_id, 40, language="ka")
    assigned.assignee_user_id = UserId()
    assigned.awaits_team = True
    waiting = conversation(business_id, 30)
    waiting.awaits_team = True
    quiet = conversation(business_id, 20, language="en")
    elsewhere = conversation(BusinessId(), 50)
    for document in (assigned, waiting, quiet, elsewhere):
        conversations.upsert(str(document.id), document)
    waiting_match = DocumentFieldMatch(field=AWAITS_TEAM, value=text("true"))

    nobody_assigned = conversations.page_by(
        feed_query(business_id, 10, missing=(ASSIGNEE,))
    )
    waiting_for_nobody = conversations.page_by(
        feed_query(
            business_id,
            10,
            matches=(feed_query(business_id, 1).where.matches[0], waiting_match),
            missing=(ASSIGNEE,),
        )
    )
    without_language = conversations.page_by(
        feed_query(business_id, 10, missing=(LANGUAGE, ASSIGNEE))
    )
    counted = conversations.count_by(
        DocumentAggregation(
            where=DocumentFilter(
                matches=(feed_query(business_id, 1).where.matches[0], waiting_match),
                missing=(ASSIGNEE,),
            )
        )
    )

    assert [c.id for c in nobody_assigned] == [waiting.id, quiet.id]
    assert [c.id for c in waiting_for_nobody] == [waiting.id]
    assert [c.id for c in without_language] == [waiting.id]
    assert [int(group.count) for group in counted] == [1]


@pytest.mark.parametrize(
    "query", ["undeclared field", "list field", "no indexed selection"]
)
def test_missing_conditions_refuse_fields_without_a_fitting_index(
    collections: CollectionFactory, query: str
) -> None:
    with pytest.raises(UndeclaredLookupFieldError, match="lookup field"):
        if query == "undeclared field":
            collections(ConversationDocument, "conversations").page_by(
                feed_query(BusinessId(), 1, missing=(DocumentFieldPath("rating"),))
            )
        elif query == "list field":
            collections(MessageDocument, "messages").count_by(
                DocumentAggregation(
                    where=DocumentFilter(
                        matches=feed_query(BusinessId(), 1).where.matches,
                        missing=(DocumentFieldPath("tool_calls[].is_error"),),
                    )
                )
            )
        else:
            collections(ConversationDocument, "conversations").count_by(
                DocumentAggregation(where=DocumentFilter(missing=(ASSIGNEE,)))
            )


def test_a_missing_condition_rides_on_the_page_order(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    stored = conversation(business_id, 10)
    conversations.upsert(str(stored.id), stored)

    page = conversations.page_by(
        DocumentPageQuery(
            where=DocumentFilter(missing=(ASSIGNEE,)),
            sort_fields=(LAST_MESSAGE_AT,),
            limit=DocumentQueryLimit(5),
        )
    )

    assert stored.id in [c.id for c in page]
