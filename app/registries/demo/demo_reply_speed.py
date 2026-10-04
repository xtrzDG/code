"""How long the demo customers waited for the assistant's chat replies."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.demo_data import DemoMessageLine
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)

MILLISECONDS_PER_SECOND: int = 1000
# Calls and the owner's test chat have no waiting customer to measure.
UNMEASURED_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.PHONE, ChannelKind.OWNER_TEST}
)


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
    conversation: ConversationDocument, line: DemoMessageLine
) -> ReplyLatencyMilliseconds | None:
    """A chat reply's wait: the pause before it in the demo script."""

    if not is_measured_reply(conversation, line):
        return None

    return ReplyLatencyMilliseconds(int(line.pause_seconds) * MILLISECONDS_PER_SECOND)
