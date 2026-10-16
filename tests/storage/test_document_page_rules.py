"""Keyset pages refuse fields without an index, on every storage."""

import pytest

from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.storage_pages import DocumentPagePosition, DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldExclusion, DocumentFilter
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import StoredDocumentKey
from tests.storage.conftest import CollectionFactory
from tests.storage.test_document_pages import (
    CREATED_AT,
    STATUS,
    conversation,
    feed_query,
    text,
)

pytestmark = pytest.mark.usefixtures("platform_scope")


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
    with pytest.raises(ValueError, match="at most 3"):
        DocumentPageQuery(
            sort_fields=(CREATED_AT, CREATED_AT, CREATED_AT, CREATED_AT),
            limit=DocumentQueryLimit(1),
        )
    with pytest.raises(ValueError, match="one value per sort field"):
        DocumentPageQuery(
            sort_fields=(CREATED_AT,),
            after=DocumentPagePosition(values=(), document_key=StoredDocumentKey("x")),
            limit=DocumentQueryLimit(1),
        )


def test_get_many_reads_the_stored_keys_only(collections: CollectionFactory) -> None:
    conversations = collections(ConversationDocument, "conversations")
    business_id = BusinessId()
    stored = [conversation(business_id, at) for at in (10, 20, 30)]
    for document in stored:
        conversations.upsert(str(document.id), document)

    found = conversations.get_many(
        [str(stored[2].id), "missing", str(stored[0].id), str(stored[2].id)]
    )

    assert sorted(str(c.id) for c in found) == sorted(
        [str(stored[0].id), str(stored[2].id)]
    )
    assert conversations.get_many([]) == []


def test_a_page_without_sort_fields_walks_in_first_write_order(
    collections: CollectionFactory,
) -> None:
    conversations = collections(ConversationDocument, "conversations")
    stored = [conversation(BusinessId(), at) for at in (50, 20, 90, 10, 70)]
    for document in stored:
        conversations.upsert(str(document.id), document)

    walked: list[ConversationDocument] = []
    after: ConversationDocument | None = None
    while True:
        page = conversations.page_by(
            DocumentPageQuery(
                sort_fields=(),
                is_descending=False,
                after=None
                if after is None
                else DocumentPagePosition(
                    values=(), document_key=StoredDocumentKey(str(after.id))
                ),
                limit=DocumentQueryLimit(2),
            )
        )
        walked.extend(page)
        if len(page) < 2:
            break
        after = page[-1]

    # Every row, in the order it was first written, whatever its fields.
    assert [document.id for document in walked] == [document.id for document in stored]
