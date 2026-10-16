"""Reading a channel back from the channels testbed's repository."""

from app.schemas.domain.channels import ChannelDocument
from tests.channels.testbed import ChannelsTestbed


def stored(testbed: ChannelsTestbed, channel: ChannelDocument) -> ChannelDocument:
    current = testbed.channel_repo.get(channel.id)
    assert current is not None
    return current
