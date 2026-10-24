"""Reading the channels testbed's inbox and outbox in assertions."""

from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.channels.testbed import ChannelsTestbed


def outbox_of(
    testbed: ChannelsTestbed, business_id: BusinessId
) -> list[OutboundMessageDocument]:
    """Every outbox message of a business, oldest first."""

    return sorted(
        (
            message
            for message in testbed.outbound_message_collection.list_all()
            if message.business_id == business_id
        ),
        key=lambda message: (int(message.created_at), str(message.id)),
    )


def inbox(testbed: ChannelsTestbed) -> list[InboundEventDocument]:
    """Every inbox event, oldest first."""

    return sorted(
        testbed.inbound_event_collection.list_all(),
        key=lambda event: (int(event.created_at), str(event.id)),
    )
