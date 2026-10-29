"""
How long the demo customers waited for the assistant's chat replies: drawn
per channel from what live replies take, so the admin's reply-speed card
shows the channels as they differ. The web chat answers in 4 to 7 seconds;
messengers in 6 to 11 (the 3-second grouping of a burst of messages, the
model, and the provider's delivery). The draw is a hash of the reply's
place in its conversation: the same seed gives the same waits.
"""

import hashlib

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.demo_data import DemoMessageLine
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)

MILLISECONDS_PER_SECOND: int = 1000
MICROSECONDS_PER_MILLISECOND: int = 1000
# Calls and the owner's test chat have no waiting customer to measure.
UNMEASURED_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.PHONE, ChannelKind.OWNER_TEST}
)
WEB_CHAT_WAIT_MS: tuple[int, int] = (4_000, 7_000)
MESSENGER_WAIT_MS: tuple[int, int] = (6_000, 11_000)
WAIT_RANGES_MS: dict[ChannelKind, tuple[int, int]] = {
    ChannelKind.WEB_CHAT: WEB_CHAT_WAIT_MS,
}
DRAW_BUCKETS: int = 2**32


def is_measured_reply(
    conversation: ConversationDocument, line: DemoMessageLine
) -> bool:
    return (
        line.author is MessageAuthor.ASSISTANT
        and not conversation.is_sandbox
        and conversation.channel not in UNMEASURED_CHANNELS
    )


def demo_reply_channel(
    conversation: ConversationDocument, line: DemoMessageLine
) -> ChannelKind | None:
    """The channel an assistant reply went out in, as live replies record it."""

    return conversation.channel if line.author is MessageAuthor.ASSISTANT else None


def demo_reply_latency(
    conversation: ConversationDocument, line: DemoMessageLine, position: int
) -> ReplyLatencyMilliseconds | None:
    """A chat reply's wait, drawn in its channel's range (None: not measured)."""

    if not is_measured_reply(conversation, line):
        return None

    low, high = WAIT_RANGES_MS.get(conversation.channel, MESSENGER_WAIT_MS)
    digest: bytes = hashlib.sha256(
        f"reply-wait|{int(conversation.created_at)}|{position}".encode()
    ).digest()
    share: float = int.from_bytes(digest[:4], "big") / DRAW_BUCKETS
    return ReplyLatencyMilliseconds(low + round(share * (high - low)))


def demo_line_pause_microseconds(
    conversation: ConversationDocument, line: DemoMessageLine, position: int
) -> int:
    """
    How long after the line before this one was written: a measured reply
    comes after its drawn wait, every other line after its script's pause.
    """

    latency: ReplyLatencyMilliseconds | None = demo_reply_latency(
        conversation, line, position
    )
    if latency is None:
        return int(line.pause_seconds) * MILLISECONDS_PER_SECOND * 1000

    return int(latency) * MICROSECONDS_PER_MILLISECOND
