"""
The worker keeps photos for the model, reads places as they came, marks
stickers, contact cards and other files unreadable, and refuses files over
the size caps or that are not pictures at all.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from tests.channels.telegram_updates import connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed
from tests.media.inbound_media_steps import (
    PAST_EVERY_BACKOFF_SECONDS,
    read_attachments,
    telegram_update,
    transcription_usage,
)
from tests.media.media_fakes import jpeg_bytes


class TestPhotosPlacesAndOtherFiles:
    def test_a_photo_is_kept_for_the_model_and_its_caption_is_the_text(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["photo-file-large"] = jpeg_bytes()

        post_update(testbed, channel, telegram_update(1))
        testbed.run_worker()

        [message] = testbed.pipeline.messages
        assert message.text == "Это блюдо есть в меню?"
        [photo] = message.attachments
        assert photo.kind is AttachmentKind.IMAGE
        assert photo.media_type == "image/jpeg"
        assert photo.problem is None
        [fetch] = testbed.media_fetcher.requests
        assert int(fetch.max_bytes) == int(testbed.settings.media.max_image_bytes)
        assert testbed.voice_transcriber.requests == []
        assert transcription_usage(testbed, business.id) == []

    def test_places_are_read_without_a_download(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        post_update(testbed, channel, telegram_update(3))
        testbed.run_worker()

        [place] = read_attachments(testbed)
        assert place.kind is AttachmentKind.LOCATION
        assert place.location is not None
        assert place.location.name == "Mtsvane Ezo"
        assert testbed.media_fetcher.requests == []

    def test_stickers_contacts_and_video_notes_are_marked_unreadable(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        for index in (4, 6, 7):
            update = telegram_update(index)
            update["update_id"] += index
            post_update(testbed, channel, update)
            testbed.run_worker()

        problems = [
            (message.attachments[0].kind, message.attachments[0].problem)
            for message in testbed.pipeline.messages
        ]
        assert problems == [
            (AttachmentKind.STICKER, AttachmentProblem.UNSUPPORTED_KIND),
            (AttachmentKind.CONTACT, AttachmentProblem.UNSUPPORTED_KIND),
            (AttachmentKind.OTHER, AttachmentProblem.UNSUPPORTED_KIND),
        ]
        assert testbed.media_fetcher.requests == []

    def test_a_declared_size_over_the_cap_is_refused_without_a_download(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        update = telegram_update(1)
        for size in update["message"]["photo"]:
            size["file_size"] = 6 * 1024 * 1024

        post_update(testbed, channel, update)
        testbed.run_worker()

        [photo] = read_attachments(testbed)
        assert photo.problem is AttachmentProblem.TOO_LARGE
        assert testbed.media_fetcher.requests == []

    def test_a_download_over_the_cap_is_too_large(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.failures["photo-file-large"] = [
            MediaTooLargeError("larger than allowed")
        ]

        post_update(testbed, channel, telegram_update(1))
        testbed.run_worker()

        [photo] = read_attachments(testbed)
        assert photo.problem is AttachmentProblem.TOO_LARGE
        assert testbed.media_storage.files == {}

    def test_a_file_the_platform_no_longer_has_is_unavailable(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.failures["photo-file-large"] = [
            MediaUnavailableError("expired")
        ]

        post_update(testbed, channel, telegram_update(1))
        testbed.run_worker()

        [photo] = read_attachments(testbed)
        assert photo.problem is AttachmentProblem.UNAVAILABLE
        assert len(testbed.media_fetcher.requests) == 1

    def test_something_that_is_not_a_picture_is_never_kept(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.media_fetcher.files["photo-file-large"] = (
            b"<!doctype html><script>alert(1)</script>"
        )

        post_update(testbed, channel, telegram_update(1))
        testbed.run_worker()

        [photo] = read_attachments(testbed)
        assert photo.problem is AttachmentProblem.UNRECOGNIZED_FORMAT
        assert testbed.media_storage.files == {}
        assert (
            testbed.message_media_repo.list_created_before(
                business.id, Microseconds(2**62)
            )
            == []
        )

    def test_a_download_outage_is_retried_then_succeeds(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.files["photo-file-large"] = jpeg_bytes()
        testbed.media_fetcher.failures["photo-file-large"] = [
            ExternalServiceError("Telegram is down")
        ]

        post_update(testbed, channel, telegram_update(1))
        testbed.run_worker()
        assert testbed.pipeline.messages == []

        testbed.clock.advance(PAST_EVERY_BACKOFF_SECONDS)
        testbed.run_worker()

        [photo] = read_attachments(testbed)
        assert photo.problem is None
        assert len(testbed.media_fetcher.requests) == 2

    def test_a_download_outage_on_the_last_try_gives_the_file_up(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.media_fetcher.failures["photo-file-large"] = [
            ExternalServiceError("Telegram is down") for _ in range(5)
        ]

        post_update(testbed, channel, telegram_update(1))
        for _ in range(5):
            testbed.run_worker()
            testbed.clock.advance(PAST_EVERY_BACKOFF_SECONDS)

        [photo] = read_attachments(testbed)
        assert photo.problem is AttachmentProblem.UNAVAILABLE
