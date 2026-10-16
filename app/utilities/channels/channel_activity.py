"""
When a channel last carried a message each way, for its health line in the
cabinet ("last message from a customer 5 minutes ago, last reply 4 minutes
ago"): the platform brought a customer message (a webhook, a widget
message) or took one of ours (a delivered outbox message, a widget answer).

The stamps are kept to the minute: a channel is written at most once a
minute per direction, however busy it is, and the write changes only the
stamp (`ChannelRepoContract.modify`), so an owner's change made meanwhile
is kept. Stamps are activity, not settings: `updated_at` stays, and no live
event is published for them.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.utilities.channels.delivery_targets import find_business_channel

ACTIVITY_STAMP_RESOLUTION_MICROSECONDS: int = 60 * 1_000_000


def stamped_at(
    channel: ChannelDocument, direction: MessageDirection
) -> Microseconds | None:
    if direction is MessageDirection.INBOUND:
        return channel.last_inbound_at

    return channel.last_outbound_at


def is_stamp_due(stamp: Microseconds | None, now: Microseconds) -> bool:
    """No stamp yet, or one at least a minute old (a clock moved back too)."""

    if stamp is None:
        return True

    age: int = int(now) - int(stamp)
    return age >= ACTIVITY_STAMP_RESOLUTION_MICROSECONDS or age < 0


def stamp_channel_activity(
    channel_repo: ChannelRepoContract,
    channel: ChannelDocument,
    direction: MessageDirection,
    now: Microseconds,
) -> None:
    """Note a message on `channel` (as read just now) unless noted this minute."""

    if not is_stamp_due(stamped_at(channel, direction), now):
        return

    channel_repo.modify(channel.business_id, channel.id, stamp_change(direction, now))


def stamp_change(
    direction: MessageDirection, now: Microseconds
) -> Callable[[ChannelDocument], ChannelDocument | None]:
    """The change that stamps a channel as stored, unless done this minute."""

    def change(current: ChannelDocument) -> ChannelDocument | None:
        if not is_stamp_due(stamped_at(current, direction), now):
            return None

        if direction is MessageDirection.INBOUND:
            current.last_inbound_at = now
        else:
            current.last_outbound_at = now
        return current

    return change


def stamp_routed_channel_activity(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    channel_id: ChannelId,
    stamp: Microseconds | None,
    now: Microseconds,
) -> None:
    """
    The same for a customer message's channel whose `last_inbound_at` was
    read with it just now (a webhook's routed message): nothing more is
    read while that stamp is of this minute.
    """

    if not is_stamp_due(stamp, now):
        return

    channel_repo.modify(
        business_id, channel_id, stamp_change(MessageDirection.INBOUND, now)
    )


def stamp_business_channel_activity(
    channel_repo: ChannelRepoContract,
    business_id: BusinessId,
    kind: ChannelKind,
    direction: MessageDirection,
    now: Microseconds,
) -> None:
    """The same for the business's channel of a kind (the website chat)."""

    channel: ChannelDocument | None = find_business_channel(
        channel_repo, business_id, kind
    )
    if channel is not None:
        stamp_channel_activity(channel_repo, channel, direction, now)
