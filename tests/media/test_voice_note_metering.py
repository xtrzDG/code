"""
The worker measures every voice note it keeps and never takes a shorter
length on the sender's word, so the MEDIA_MAX_VOICE_SECONDS cap holds for
every channel; transcription is metered by the seconds the service says
it billed when it says so (both took the stated length before).
"""

from app.schemas.constants.media import AttachmentProblem
from tests.channels.telegram_updates import connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.media.inbound_media_steps import (
    read_attachments,
    telegram_update,
    transcription_usage,
)
from tests.media.media_fakes import ogg_opus_bytes


class TestStatedLengths:
    def test_a_short_stated_length_does_not_hide_a_long_file(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes(seconds=3600)
        update = telegram_update(0)
        update["message"]["voice"]["duration"] = 2

        post_update(testbed, channel, update)
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.problem is AttachmentProblem.TOO_LONG
        assert voice.duration_seconds == 3600
        assert testbed.voice_transcriber.requests == []

    def test_a_longer_stated_length_still_counts(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes(seconds=4)
        update = telegram_update(0)
        update["message"]["voice"]["duration"] = 9

        post_update(testbed, channel, update)
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.duration_seconds == 9
        [usage] = transcription_usage(testbed, business.id)
        assert int(usage.quantity) == 9


class TestBilledSeconds:
    def test_the_seconds_the_service_billed_are_metered(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes(seconds=7)
        testbed.voice_transcriber.billed_seconds = 45

        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.duration_seconds == 7
        [usage] = transcription_usage(testbed, business.id)
        assert int(usage.quantity) == 45

    def test_without_a_billed_count_the_measured_length_is_metered(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes(seconds=7)

        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()

        [usage] = transcription_usage(testbed, business.id)
        assert int(usage.quantity) == 7
