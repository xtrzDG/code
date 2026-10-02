"""
The inbox and the outbox on Postgres: one event per redelivered message and
one outbox row per idempotency key, even for concurrent writers; the
waiting messages of a recipient in order; the outbox under row-level
security.
"""

import threading

import pytest
from typed_time_provider import Microseconds

from app.repositories.delivery_repositories import (
    InboundEventRepository,
    OutboundMessageRepository,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import (
    InboundEventKind,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.utilities.deliveries.delivery_keys import (
    derive_inbound_event_id,
    derive_outbound_message_id,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import PostgresCollectionFactory

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")

RECIPIENT: OutboundRecipientKey = OutboundRecipientKey("customer:channel_1:9001")


def event(business_id: BusinessId | None, message_id: str) -> InboundEventDocument:
    provider_message_id = ProviderMessageId(message_id)
    return InboundEventDocument(
        id=derive_inbound_event_id(
            business_id, ChannelKind.TELEGRAM, provider_message_id
        ),
        business_id=business_id,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=ChannelKind.TELEGRAM,
        provider_message_id=provider_message_id,
    )


def reply(
    business_id: BusinessId, key: str, created_at: int
) -> OutboundMessageDocument:
    idempotency_key = OutboundIdempotencyKey(key)
    return OutboundMessageDocument(
        id=derive_outbound_message_id(business_id, idempotency_key),
        business_id=business_id,
        kind=OutboundMessageKind.CUSTOMER_REPLY,
        idempotency_key=idempotency_key,
        recipient_key=RECIPIENT,
        text=MessageText("See you at 19:00."),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def test_a_message_delivered_concurrently_is_stored_once(
    postgres_collections: PostgresCollectionFactory,
) -> None:
    collection = postgres_collections(InboundEventDocument, "inbound_events")
    events = InboundEventRepository(collection)
    business_id = BusinessId()
    results: list[bool] = []

    def deliver() -> None:
        results.append(events.insert_if_new(event(business_id, "42")))

    threads = [threading.Thread(target=deliver) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False] * 5 + [True]
    # The unique index refuses the same message stored under another key,
    # for a business and for a platform event (no business) alike.
    stored_again = event(business_id, "42").model_copy(
        update={"id": event(business_id, "other").id}
    )
    assert collection.insert_if_absent(str(stored_again.id), stored_again) is False
    assert events.insert_if_new(event(None, "7")) is True
    platform_again = event(None, "7").model_copy(update={"id": event(None, "8").id})
    assert collection.insert_if_absent(str(platform_again.id), platform_again) is False
    assert events.get(business_id, event(business_id, "42").id) is not None
    assert events.get(BusinessId(), event(business_id, "42").id) is None


def test_the_outbox_keeps_one_row_per_key_and_lists_waiting_messages_in_order(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    outbox = OutboundMessageRepository(
        postgres_collections(OutboundMessageDocument, "outbound_messages")
    )
    business_id, other_business = BusinessId(), BusinessId()
    second, first = reply(business_id, "b", 2), reply(business_id, "a", 1)
    assert outbox.insert_if_new(second)
    assert outbox.insert_if_new(first)
    assert not outbox.insert_if_new(reply(business_id, "a", 3))
    assert outbox.insert_if_new(reply(other_business, "a", 1))

    with storage_scope.scoped_to_business(business_id):
        waiting = outbox.list_pending_for_recipient(business_id, RECIPIENT)
        delivered = outbox.update(
            business_id,
            first.id,
            lambda message: message.model_copy(
                update={"status": OutboundMessageStatus.DELIVERED}
            ),
        )
        foreign = outbox.get(business_id, reply(other_business, "a", 1).id)

    assert [message.id for message in waiting] == [first.id, second.id]
    assert delivered is not None
    assert delivered.status is OutboundMessageStatus.DELIVERED
    assert foreign is None
    assert [
        message.id
        for message in outbox.list_pending_for_recipient(business_id, RECIPIENT)
    ] == [second.id]
