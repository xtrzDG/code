"""
The demo channels' health line: when each channel last brought a
customer message and carried one of ours, taken from the month of demo
conversations (a real channel stamps them as messages come and go).
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.demo_data import DemoBusinessActivity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId

type ChannelStamps = dict[tuple[ChannelKind, MessageDirection], Microseconds]


def latest_channel_messages(activity: DemoBusinessActivity) -> ChannelStamps:
    """The newest message per channel and direction (test chats left out)."""

    channels: dict[ConversationId, ChannelKind] = {
        conversation.id: conversation.channel
        for conversation in activity.conversations
        if not conversation.is_sandbox
    }
    latest: ChannelStamps = {}
    for message in activity.messages:
        channel: ChannelKind | None = channels.get(message.conversation_id)
        if channel is None:
            continue

        key = (channel, message.direction)
        if key not in latest or int(message.created_at) > int(latest[key]):
            latest[key] = message.created_at

    return latest


def stamp_demo_channels(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    activity: DemoBusinessActivity,
) -> None:
    """Give the business's channels the stamps of their demo messages."""

    stamps: ChannelStamps = latest_channel_messages(activity)
    for channel in channel_repo.list_by_business(business_id):
        inbound: Microseconds | None = stamps.get(
            (channel.kind, MessageDirection.INBOUND)
        )
        outbound: Microseconds | None = stamps.get(
            (channel.kind, MessageDirection.OUTBOUND)
        )
        if inbound is None and outbound is None:
            continue

        def change(
            current: ChannelDocument,
            inbound_at: Microseconds | None = inbound,
            outbound_at: Microseconds | None = outbound,
        ) -> ChannelDocument:
            current.last_inbound_at = inbound_at
            current.last_outbound_at = outbound_at
            return current

        channel_repo.modify(business_id, channel.id, change)
