"""
The delivery state next to each staff reply of a transcript, read from the
outbox messages that carry them: one read for a page of messages.
"""

from collections.abc import Sequence

from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.conversation_feed.conversation_views import MessageView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.utilities.deliveries.customer_message_keys import (
    staff_reply_idempotency_key,
)
from app.utilities.deliveries.delivery_keys import derive_outbound_message_id
from app.utilities.deliveries.delivery_views import build_delivery_view


def staff_reply_outbox_id(
    business_id: BusinessId,
    message_id: MessageId,
) -> OutboundMessageId:
    """The outbox message of a staff reply (derived from the reply's id)."""

    return derive_outbound_message_id(
        business_id, staff_reply_idempotency_key(message_id)
    )


def with_staff_deliveries(
    business_id: BusinessId,
    messages: Sequence[MessageDocument],
    views: list[MessageView],
    outbound_message_repo: OutboundMessageRepoContract,
) -> list[MessageView]:
    """
    The views with `delivery` set for each staff reply that went through
    the outbox (website chat replies and older messages have none).
    """

    outbox_ids: list[OutboundMessageId] = [
        staff_reply_outbox_id(business_id, message.id)
        for message in messages
        if message.author is MessageAuthor.STAFF
    ]
    if not outbox_ids:
        return views

    by_reply: dict[MessageId, OutboundMessageDocument] = {
        outbound.source_message_id: outbound
        for outbound in outbound_message_repo.get_many(business_id, outbox_ids)
        if outbound.source_message_id is not None
    }
    return [
        view
        if view.id not in by_reply
        else view.model_copy(
            update={"delivery": build_delivery_view(by_reply[view.id])}
        )
        for view in views
    ]
