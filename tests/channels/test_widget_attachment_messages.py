"""
A widget message that names uploads: each must be its own visitor's, in
this business, not sent yet and at most a day old; the worker reads the
files as it reads a WhatsApp customer's (voice notes transcribed and
metered, photos kept for the model).
"""

import threading

from app.schemas.constants.media import AttachmentKind
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.use_cases.channels.uploads.message_uploads import (
    inbound_attachment_of,
    read_message_uploads,
)
from app.utilities.media.media_paths import MEDIA_DIRECTORY
from tests.channels.outbox_reads import inbox
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.widget_upload_bed import OTHER_VISITOR, WidgetUploadBed
from tests.media.inbound_media_steps import transcription_usage
from tests.media.upload_files import jpeg_photo, png_photo, webm_recording

DAY_SECONDS: int = 24 * 60 * 60


class TestBinding:
    def test_a_message_may_carry_uploads_without_text(self) -> None:
        bed = WidgetUploadBed()
        photo_id = bed.uploaded_id(png_photo(), "image/png")

        response = bed.send([photo_id])

        assert response.status_code == 202
        [event] = inbox(bed.testbed)
        assert event.customer_message is not None
        [attachment] = event.customer_message.attachments
        assert attachment.kind is AttachmentKind.IMAGE
        assert str(attachment.provider_media_id) == str(
            bed.stored_upload(photo_id).storage_path
        )
        assert bed.stored_upload(photo_id).attached_at is not None

    def test_a_message_without_text_or_uploads_is_refused(self) -> None:
        bed = WidgetUploadBed()

        response = bed.send([])

        assert response.status_code == 422
        assert inbox(bed.testbed) == []

    def test_another_visitor_cannot_send_my_upload(self) -> None:
        bed = WidgetUploadBed()
        photo_id = bed.uploaded_id(png_photo(), "image/png")

        stolen = bed.send([photo_id], "look", session_key=OTHER_VISITOR)

        assert stolen.status_code == 404
        assert bed.stored_upload(photo_id).attached_at is None
        assert inbox(bed.testbed) == []

    def test_an_upload_is_sent_once(self) -> None:
        bed = WidgetUploadBed()
        photo_id = bed.uploaded_id(png_photo(), "image/png")

        first = bed.send([photo_id], "first")
        again = bed.send([photo_id], "again")

        assert (first.status_code, again.status_code) == (202, 404)
        assert len(inbox(bed.testbed)) == 1

    def test_an_upload_of_another_business_is_not_found(self) -> None:
        bed = WidgetUploadBed()
        other_business = enable_widget(bed.testbed)
        photo_id = bed.uploaded_id(png_photo(), "image/png")

        response = bed.send([photo_id], "hi", business_id=other_business.id)

        assert response.status_code == 404
        assert bed.stored_upload(photo_id).attached_at is None

    def test_an_upload_older_than_a_day_is_not_found(self) -> None:
        bed = WidgetUploadBed()
        photo_id = bed.uploaded_id(png_photo(), "image/png")
        bed.testbed.clock.advance(DAY_SECONDS + 1)

        response = bed.send([photo_id], "late")

        assert response.status_code == 404

    def test_an_upload_named_twice_or_five_uploads_are_refused(self) -> None:
        bed = WidgetUploadBed()
        photo_id = bed.uploaded_id(png_photo(), "image/png")
        unknown = [str(WidgetUploadId()) for _ in range(5)]

        twice = bed.send([photo_id, photo_id])
        too_many = bed.send(unknown)

        assert (twice.status_code, too_many.status_code) == (422, 422)
        assert bed.stored_upload(photo_id).attached_at is None

    def test_of_two_messages_racing_for_one_upload_one_is_queued(self) -> None:
        bed = WidgetUploadBed()
        photo_id = bed.uploaded_id(png_photo(), "image/png")
        testbed = bed.testbed
        # Both messages passed their checks before either claimed the file.
        uploads = read_message_uploads(
            testbed.widget_upload_repo,
            bed.business.id,
            WidgetSessionKey(SESSION_KEY),
            [WidgetUploadId(photo_id)],
            testbed.wall_clock.now_unix(),
        )
        accepted = bed.accepted_message(uploads, [inbound_attachment_of(uploads[0])])
        start = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def queue() -> None:
            start.wait()
            try:
                testbed.queue_widget_message.run(accepted)
                outcome = "queued"
            except NotFoundError:
                outcome = "not_found"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=queue) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(outcomes) == ["not_found", "queued"]
        assert len(inbox(testbed)) == 1


class TestTheWorkerReadsTheFiles:
    def test_a_voice_note_is_transcribed_as_a_whatsapp_one(self) -> None:
        bed = WidgetUploadBed()
        testbed = bed.testbed
        testbed.voice_transcriber.texts = ["Do you have a table for four tonight?"]
        voice_id = bed.uploaded_id(webm_recording(9), "audio/webm;codecs=opus")

        assert bed.send([voice_id]).status_code == 202
        testbed.run_worker()

        [message] = testbed.pipeline.messages
        [voice] = message.attachments
        assert voice.kind is AttachmentKind.AUDIO
        assert voice.transcript == "Do you have a table for four tonight?"
        assert voice.duration_seconds == 9
        assert voice.problem is None
        assert str(voice.storage_path).startswith(
            f"{MEDIA_DIRECTORY}/{bed.business.id}/"
        )
        [heard] = testbed.voice_transcriber.requests
        assert heard.audio.media_type == "audio/webm"
        [usage] = transcription_usage(testbed, bed.business.id)
        assert int(usage.quantity) == 9
        # The platforms' downloader was never asked: the file was ours.
        assert testbed.media_fetcher.requests == []

    def test_a_photo_reaches_the_model_without_its_metadata(self) -> None:
        bed = WidgetUploadBed()
        testbed = bed.testbed
        photo_id = bed.uploaded_id(jpeg_photo(), "image/jpeg")

        assert bed.send([photo_id], "Is this dish vegan?").status_code == 202
        testbed.run_worker()

        [message] = testbed.pipeline.messages
        assert message.text == "Is this dish vegan?"
        [photo] = message.attachments
        assert photo.kind is AttachmentKind.IMAGE
        assert photo.media_id is not None
        stored = testbed.message_media_repo.get(bed.business.id, photo.media_id)
        assert stored is not None
        kept = testbed.media_storage.files[
            (str(bed.business.id), str(stored.storage_path))
        ]
        assert kept.content == bed.stored_bytes(photo_id)
