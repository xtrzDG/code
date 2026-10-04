"""
The reply-speed queries on both stores (migration 1090): one customer's
recent inbox events by creation time (grouping quick messages), and the
assistant replies of a week per channel and latency bucket.
"""

import pytest
from typed_time_provider import Microseconds

from app.repositories.conversation_repositories import MessageRepository
from app.repositories.delivery_repositories import InboundEventRepository
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

SECOND: int = 1_000_000
START: int = 1_790_812_800 * SECOND
BUCKETS: list[ReplyLatencyMilliseconds] = [
    ReplyLatencyMilliseconds(start) for start in (0, 1_000, 5_000, 15_000)
]


def event(business_id: BusinessId, message_id: str, at: int) -> InboundEventDocument:
    provider_message_id = ProviderMessageId(message_id)
    return InboundEventDocument(
        id=derive_inbound_event_id(
            business_id, ChannelKind.TELEGRAM, provider_message_id
        ),
        business_id=business_id,
        kind=InboundEventKind.CUSTOMER_MESSAGE,
        channel=ChannelKind.TELEGRAM,
        provider_message_id=provider_message_id,
        created_at=Microseconds(at),
        updated_at=Microseconds(at),
    )


def reply(
    business_id: BusinessId,
    channel: ChannelKind | None,
    latency_ms: int | None,
    at: int,
    author: MessageAuthor = MessageAuthor.ASSISTANT,
) -> MessageDocument:
    return MessageDocument(
        conversation_id=ConversationId(),
        business_id=business_id,
        direction=MessageDirection.OUTBOUND,
        author=author,
        text=MessageText("Yes, we are open."),
        channel=channel,
        reply_latency_ms=(
            None if latency_ms is None else ReplyLatencyMilliseconds(latency_ms)
        ),
        created_at=Microseconds(at),
        updated_at=Microseconds(at),
    )


def test_inbox_events_of_a_business_are_found_by_creation_time(
    collections: CollectionFactory,
) -> None:
    events = InboundEventRepository(collections(InboundEventDocument, "inbound_events"))
    business_id, other_business = BusinessId(), BusinessId()
    for index, at in enumerate((START, START + SECOND, START + 90 * SECOND)):
        events.insert_if_new(event(business_id, f"chat:{index}", at))
    events.insert_if_new(event(other_business, "chat:9", START + SECOND))

    found = events.list_created_between(
        business_id, Microseconds(START), Microseconds(START + 60 * SECOND)
    )

    assert sorted(str(found_event.provider_message_id) for found_event in found) == [
        "chat:0",
        "chat:1",
    ]


def test_reply_latencies_are_counted_per_channel_and_bucket(
    collections: CollectionFactory,
) -> None:
    messages = MessageRepository(collections(MessageDocument, "messages"))
    business_id = BusinessId()
    messages.save_many(
        [
            reply(business_id, ChannelKind.WHATSAPP, 800, START),
            reply(business_id, ChannelKind.WHATSAPP, 2_000, START + SECOND),
            reply(business_id, ChannelKind.WHATSAPP, 3_000, START + 2 * SECOND),
            reply(business_id, ChannelKind.TELEGRAM, 20_000, START + 3 * SECOND),
            # Left out: unmeasured, staff, before the week, other business.
            reply(business_id, ChannelKind.TELEGRAM, None, START + 4 * SECOND),
            reply(
                business_id,
                ChannelKind.TELEGRAM,
                9_000,
                START,
                author=MessageAuthor.STAFF,
            ),
            reply(business_id, ChannelKind.TELEGRAM, 9_000, START - SECOND),
            reply(BusinessId(), ChannelKind.WHATSAPP, 9_000, START),
        ]
    )

    counts = messages.count_reply_latencies(business_id, Microseconds(START), BUCKETS)

    assert sorted(
        (count.channel.value, int(count.bucket), int(count.count)) for count in counts
    ) == [("telegram", 3, 1), ("whatsapp", 0, 1), ("whatsapp", 1, 2)]
