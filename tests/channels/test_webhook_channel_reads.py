"""
A Telegram webhook reads its channel once: to verify it. The channel's
activity stamp comes from that read (written once a minute), and only a
button tap reads the channel again, to answer the tap.
"""

from collections.abc import Callable

import pytest

from app.repositories.business_repositories import ChannelRepository
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.channels.prefixed_id import ChannelId
from tests.channels.channels_payloads import telegram_ok
from tests.channels.stored_channels import stored
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.test_telegram_taps import tap_update
from tests.channels.testbed import ChannelsTestbed


@pytest.fixture
def channel_reads(monkeypatch: pytest.MonkeyPatch) -> list[ChannelId]:
    """The channels read by id, in order (every repository instance)."""

    reads: list[ChannelId] = []
    read: Callable[[ChannelRepository, ChannelId], ChannelDocument | None] = (
        ChannelRepository.get
    )

    def counted(
        repository: ChannelRepository, channel_id: ChannelId
    ) -> ChannelDocument | None:
        reads.append(channel_id)
        return read(repository, channel_id)

    monkeypatch.setattr(ChannelRepository, "get", counted)
    return reads


def test_a_typed_message_reads_its_channel_once(
    channel_reads: list[ChannelId],
) -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    received_at = testbed.clock.now_microseconds()

    first = post_update(testbed, channel, build_update(message_id=1))
    testbed.clock.advance(20)
    second = post_update(testbed, channel, build_update(message_id=2))

    assert (first.status_code, second.status_code) == (200, 200)
    assert channel_reads == [channel.id, channel.id]
    # The first message stamped the channel; the second, within the
    # minute, wrote nothing.
    assert stored(testbed, channel).last_inbound_at == received_at


def test_a_stale_stamp_is_written_without_reading_the_channel_again(
    channel_reads: list[ChannelId],
) -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update(message_id=1))
    testbed.clock.advance(61)
    later = testbed.clock.now_microseconds()
    channel_reads.clear()

    post_update(testbed, channel, build_update(message_id=2))

    assert channel_reads == [channel.id]
    assert stored(testbed, channel).last_inbound_at == later


def test_only_a_tap_reads_the_channel_to_answer_it(
    channel_reads: list[ChannelId],
) -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    testbed.telegram_transport.respond(
        "POST", r"/answerCallbackQuery$", telegram_ok(True)
    )
    testbed.telegram_transport.respond("POST", r"/editMessageText$", telegram_ok({}))

    tapped = post_update(testbed, channel, tap_update())

    assert tapped.status_code == 200
    assert channel_reads == [channel.id, channel.id]
    assert any(
        request.url.path.endswith("/answerCallbackQuery")
        for request in testbed.telegram_transport.requests
    )
