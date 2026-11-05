"""
The worker reads what a Telegram customer sent before the assistant's turn:
voice notes are downloaded, kept encrypted and transcribed (metered), photos
kept for the model, places read as they came, and everything else marked
as unreadable, so it is answered rather than ignored.
"""

from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import (
    TranscriptionNotConfiguredError,
)
from app.utilities.media.media_paths import MEDIA_DIRECTORY
from tests.channels.channels_settings import TELEGRAM_BOT_TOKEN
from tests.channels.telegram_updates import connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.media.inbound_media_steps import (
    PAST_EVERY_BACKOFF_SECONDS,
    read_attachments,
    telegram_update,
    transcription_usage,
)
from tests.media.media_fakes import ogg_opus_bytes


class TestVoiceNotes:
    def test_a_voice_note_is_kept_transcribed_and_metered(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes(seconds=7)
        testbed.voice_transcriber.texts = ["Здравствуйте, есть столик на четверых?"]

        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.kind is AttachmentKind.AUDIO
        assert voice.transcript == "Здравствуйте, есть столик на четверых?"
        assert voice.duration_seconds == 7
        assert voice.problem is None
        assert voice.media_id is not None
        assert str(voice.storage_path).startswith(f"{MEDIA_DIRECTORY}/{business.id}/")

        [fetch] = testbed.media_fetcher.requests
        assert fetch.credential == TELEGRAM_BOT_TOKEN
        assert int(fetch.max_bytes) == int(testbed.settings.media.max_voice_bytes)
        [heard] = testbed.voice_transcriber.requests
        assert heard.audio.media_type == "audio/ogg"
        assert heard.keywords == [business.name]
        assert heard.language_hints[0] == business.default_language

        stored = testbed.message_media_repo.get(business.id, voice.media_id)
        assert stored is not None
        assert stored.transcript == voice.transcript
        assert (
            str(business.id),
            str(stored.storage_path),
        ) in testbed.media_storage.files
        [usage] = transcription_usage(testbed, business.id)
        assert int(usage.quantity) == 7
        assert int(usage.cost_micro_usd) > 0

    def test_a_turn_that_runs_again_neither_downloads_nor_pays_twice(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes()
        testbed.pipeline.interruptions = [ExternalServiceError("model timed out")]

        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()
        testbed.clock.advance(PAST_EVERY_BACKOFF_SECONDS)
        testbed.run_worker()

        assert len(testbed.pipeline.messages) == 2
        assert len(testbed.media_fetcher.requests) == 1
        assert len(testbed.voice_transcriber.requests) == 1
        assert len(transcription_usage(testbed, business.id)) == 1
        first, second = testbed.pipeline.messages
        assert first.attachments == second.attachments

    def test_a_voice_note_without_words_is_not_understood(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes()
        testbed.voice_transcriber.texts = ["   "]

        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.problem is AttachmentProblem.NOT_UNDERSTOOD
        assert voice.transcript is None
        # The service listened: the seconds are paid for all the same.
        assert len(transcription_usage(testbed, business.id)) == 1

    def test_a_voice_note_over_the_length_cap_is_not_sent(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.files["audio-file-0001"] = ogg_opus_bytes(seconds=31)
        update = telegram_update(8)
        update["message"]["audio"]["duration"] = 3600

        post_update(testbed, channel, update)
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.problem is AttachmentProblem.TOO_LONG
        assert testbed.voice_transcriber.requests == []

    def test_without_speech_to_text_the_customer_is_asked_to_write(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes()
        testbed.voice_transcriber.failures = [TranscriptionNotConfiguredError("no key")]

        post_update(testbed, channel, telegram_update(0))
        testbed.run_worker()

        [voice] = read_attachments(testbed)
        assert voice.problem is AttachmentProblem.NOT_UNDERSTOOD

    def test_a_transcription_outage_is_retried_and_given_up_on_the_last_try(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.files["voice-file-0001"] = ogg_opus_bytes()
        testbed.voice_transcriber.failures = [
            ExternalServiceError("OpenAI is down") for _ in range(5)
        ]

        post_update(testbed, channel, telegram_update(0))
        for _ in range(5):
            testbed.run_worker()
            testbed.clock.advance(PAST_EVERY_BACKOFF_SECONDS)

        [voice] = read_attachments(testbed)
        assert voice.problem is AttachmentProblem.NOT_UNDERSTOOD
        # The file was downloaded once and kept for every try.
        assert len(testbed.media_fetcher.requests) == 1
        assert len(testbed.voice_transcriber.requests) == 5
