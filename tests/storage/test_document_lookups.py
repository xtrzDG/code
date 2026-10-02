"""Indexed queries of the document store: the same results in memory and on Postgres."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldOrder,
    DocumentFieldRange,
)
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText
from tests.storage.conftest import CollectionFactory

PHONE = DocumentFieldPath("phone_number")
IDENTITIES = DocumentFieldPath("channel_identities[].channel_user_id")
CONVERSATION = DocumentFieldPath("conversation_id")
DIRECTION = DocumentFieldPath("direction")
CREATED_AT = DocumentFieldPath("created_at")
BUSINESS = DocumentFieldPath("business_id")


def match(field: DocumentFieldPath, value: str) -> DocumentFieldMatch:
    return DocumentFieldMatch(field=field, value=DocumentFieldText(value))


def between(lower: int | None, upper: int | None) -> DocumentFieldRange:
    return DocumentFieldRange(
        field=CREATED_AT,
        lower=None if lower is None else DocumentFieldInteger(lower),
        upper=None if upper is None else DocumentFieldInteger(upper),
    )


def contact(phone: str, *user_ids: str, business_id: BusinessId) -> ContactDocument:
    return ContactDocument(
        business_id=business_id,
        phone_number=E164PhoneNumber(phone),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM, channel_user_id=ChannelUserId(u)
            )
            for u in user_ids
        ],
    )


def message(
    conversation_id: ConversationId,
    created_at: int,
    direction: MessageDirection = MessageDirection.INBOUND,
    business_id: BusinessId | None = None,
) -> MessageDocument:
    return MessageDocument(
        conversation_id=conversation_id,
        business_id=BusinessId() if business_id is None else business_id,
        direction=direction,
        author=(
            MessageAuthor.CUSTOMER
            if direction is MessageDirection.INBOUND
            else MessageAuthor.ASSISTANT
        ),
        text=MessageText("Hello"),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def test_text_lookups_find_the_first_written_matches(
    collections: CollectionFactory,
) -> None:
    contacts = collections(ContactDocument, "contacts")
    business_id = BusinessId()
    first = contact("+995555123456", business_id=business_id)
    second = contact("+995555000000", business_id=business_id)
    third = contact("+995555123456", business_id=BusinessId())
    for stored in (first, second, third):
        contacts.upsert(str(stored.id), stored)

    found = contacts.list_by_fields([match(PHONE, "+995555123456")])
    same_business = contacts.list_by_fields(
        [match(PHONE, "+995555123456"), match(BUSINESS, str(business_id))]
    )

    assert [c.id for c in found] == [first.id, third.id]
    assert [c.id for c in same_business] == [first.id]
    assert contacts.list_by_fields([match(PHONE, "+1")]) == []
    one = contacts.find_one_by_field(PHONE, DocumentFieldText("+995555123456"))
    assert one is not None and one.id == first.id
    assert contacts.find_one_by_field(PHONE, DocumentFieldText("+1")) is None
    limited = contacts.list_by_fields(
        [match(PHONE, "+995555123456")], limit=DocumentQueryLimit(1)
    )
    assert [c.id for c in limited] == [first.id]


def test_list_field_lookups_follow_every_change(collections: CollectionFactory) -> None:
    contacts = collections(ContactDocument, "contacts")
    business_id = BusinessId()
    first = contact("+995555123456", "tg-1", "tg-2", business_id=business_id)
    second = contact("+995555000000", "tg-2", business_id=business_id)
    for stored in (first, second):
        contacts.upsert(str(stored.id), stored)

    assert [c.id for c in contacts.list_by_fields([match(IDENTITIES, "tg-2")])] == [
        first.id,
        second.id,
    ]
    first.channel_identities = [
        ChannelIdentity(
            channel=ChannelKind.WHATSAPP, channel_user_id=ChannelUserId("w")
        )
    ]
    contacts.upsert(str(first.id), first)
    contacts.delete(str(second.id))

    assert contacts.list_by_fields([match(IDENTITIES, "tg-2")]) == []
    assert contacts.list_by_fields([match(IDENTITIES, "tg-1")]) == []
    changed = contacts.find_one_by_field(IDENTITIES, DocumentFieldText("w"))
    assert changed is not None and changed.id == first.id
    assert contacts.modify(str(first.id), lambda c: c) is not None
    assert [c.id for c in contacts.list_by_fields([match(IDENTITIES, "w")])] == [
        first.id
    ]


def test_ranges_counts_and_orders_agree(collections: CollectionFactory) -> None:
    messages = collections(MessageDocument, "messages")
    conversation_id = ConversationId()
    times = [30, 10, 20, 20, 40]
    stored = [message(conversation_id, created_at) for created_at in times]
    stored.append(message(conversation_id, 25, MessageDirection.OUTBOUND))
    stored.append(message(ConversationId(), 20))
    for document in stored:
        messages.upsert(str(document.id), document)
    of_conversation = [match(CONVERSATION, str(conversation_id))]
    inbound = [*of_conversation, match(DIRECTION, MessageDirection.INBOUND.value)]

    ascending = messages.list_by_fields(
        of_conversation, DocumentFieldOrder(field=CREATED_AT)
    )
    descending = messages.list_by_fields(
        of_conversation, DocumentFieldOrder(field=CREATED_AT, is_descending=True)
    )
    in_range = messages.list_by_range(between(20, 40), inbound)
    newest = messages.list_by_range(
        between(20, None), inbound, is_descending=True, limit=DocumentQueryLimit(2)
    )

    assert [m.id for m in ascending] == [stored[i].id for i in (1, 2, 3, 5, 0, 4)]
    # Ties keep the first-write order in both directions.
    assert [m.id for m in descending] == [stored[i].id for i in (4, 0, 5, 2, 3, 1)]
    assert [m.id for m in in_range] == [stored[i].id for i in (2, 3, 0)]
    assert [m.id for m in newest] == [stored[4].id, stored[0].id]
    assert messages.count_by_fields(inbound) == 5
    assert messages.count_by_fields(inbound, between(None, 21)) == 3
    assert messages.count_by_fields([match(CONVERSATION, "none")]) == 0


def test_delete_by_range_removes_only_the_matching_documents(
    collections: CollectionFactory,
) -> None:
    messages = collections(MessageDocument, "messages")
    conversation_id = ConversationId()
    old = [message(conversation_id, created_at) for created_at in (5, 6, 7)]
    kept = [message(conversation_id, 50), message(ConversationId(), 6)]
    for document in (*old, *kept):
        messages.upsert(str(document.id), document)

    deleted = messages.delete_by_range(
        between(None, 10), [match(CONVERSATION, str(conversation_id))]
    )

    assert deleted == 3
    assert {m.id for m in messages.list_all()} == {d.id for d in kept}
    assert messages.delete_by_range(between(None, 10), [match(CONVERSATION, "x")]) == 0


def test_insert_if_absent_never_overwrites(collections: CollectionFactory) -> None:
    contacts = collections(ContactDocument, "contacts")
    first = contact("+995555123456", business_id=BusinessId())
    second = contact("+995555000000", business_id=first.business_id)

    assert contacts.insert_if_absent("receipt-key", first) is True
    assert contacts.insert_if_absent("receipt-key", second) is False
    stored = contacts.get("receipt-key")
    assert stored is not None and stored.id == first.id


@pytest.mark.parametrize(
    "query",
    [
        "undeclared match",
        "match on an integer field",
        "range on a text field",
        "order by a text field",
        "list field in a range",
        "filter field alone",
        "filter field with the business only",
    ],
)
def test_undeclared_lookup_fields_are_refused_on_every_storage(
    collections: CollectionFactory,
    query: str,
) -> None:
    messages = collections(MessageDocument, "messages")
    text_range = DocumentFieldRange(field=DIRECTION, lower=DocumentFieldInteger(1))
    with pytest.raises(UndeclaredLookupFieldError, match="lookup field"):
        if query == "undeclared match":
            messages.list_by_fields([match(DocumentFieldPath("text"), "Hello")])
        elif query == "match on an integer field":
            messages.find_one_by_field(CREATED_AT, DocumentFieldText("10"))
        elif query == "range on a text field":
            messages.count_by_fields([], text_range)
        elif query == "order by a text field":
            messages.list_by_fields([], DocumentFieldOrder(field=DIRECTION))
        elif query == "list field in a range":
            messages.delete_by_range(
                DocumentFieldRange(field=IDENTITIES, upper=DocumentFieldInteger(1))
            )
        elif query == "filter field alone":
            messages.list_by_fields([match(DIRECTION, "inbound")])
        else:
            messages.count_by_fields(
                [match(DIRECTION, "inbound"), match(BUSINESS, str(BusinessId()))]
            )


def test_a_range_needs_a_bound() -> None:
    with pytest.raises(ValueError, match="bound"):
        DocumentFieldRange(field=CREATED_AT)
