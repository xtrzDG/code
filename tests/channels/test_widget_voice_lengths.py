"""
The upload route measures a voice note from its audio, not only from what
its container claims: a ten-minute or one-minute-and-a-bit recording whose
header, block times, last page or sample tables were forged to say one
second is refused (each passed as 1 s before), while recordings of real
encoders (Chromium's MediaRecorder, ffmpeg) are taken and transcribed.
"""

import struct
from pathlib import Path
from typing import Any

import pytest

from app.schemas.constants.media import AttachmentKind
from app.schemas.typings.media.constrained_integers import AudioDurationSeconds
from tests.channels.widget_upload_bed import WidgetUploadBed
from tests.media.inbound_media_steps import transcription_usage
from tests.media.mp4_files import fragmented_mp4_recording, mp4_recording
from tests.media.recording_files import (
    ogg_opus_recording,
    ogg_page,
    webm_opus_stream,
    webm_recording,
)

RECORDINGS: Path = Path(__file__).parents[1] / "media" / "recordings"
# One second over the bed's MEDIA_MAX_VOICE_SECONDS (60).
OVER_THE_CAP: int = 61


def refusal(response: Any) -> str:
    assert response.status_code == 422, response.text
    code: str = response.json()["reasons"][0]["code"]
    return code


class TestForgedLengths:
    def test_a_webm_header_claiming_a_second_does_not_pass(self) -> None:
        bed = WidgetUploadBed()
        forged = webm_recording(600, header_duration=True).replace(
            struct.pack(">d", 600_000.0), struct.pack(">d", 1000.0)
        )
        # 61 s of 60 ms packets, every block at 0 ms, the header saying 1 s.
        squeezed = webm_opus_stream(1017, spacing_ms=0, duration_ms=1000.0)

        assert refusal(bed.upload(forged, "audio/webm")) == "voice_too_long"
        assert refusal(bed.upload(squeezed, "audio/webm")) == "voice_too_long"
        assert bed.testbed.media_storage.files == {}

    def test_an_ogg_last_page_claiming_a_second_does_not_pass(self) -> None:
        bed = WidgetUploadBed()
        forged = ogg_opus_recording(OVER_THE_CAP, last_granule=48_000)
        appended = ogg_opus_recording(OVER_THE_CAP) + ogg_page([b"\xf8"], 48_000, 99)

        assert refusal(bed.upload(forged, "audio/ogg")) == "voice_too_long"
        assert refusal(bed.upload(appended, "audio/ogg")) == "unreadable_file"
        assert bed.testbed.media_storage.files == {}

    def test_mp4_tables_claiming_a_second_do_not_pass(self) -> None:
        bed = WidgetUploadBed()
        plain = mp4_recording(OVER_THE_CAP, claimed_seconds=1)
        fragmented = fragmented_mp4_recording(OVER_THE_CAP, claimed_seconds=1)

        assert refusal(bed.upload(plain, "audio/mp4")) == "voice_too_long"
        assert refusal(bed.upload(fragmented, "audio/mp4")) == "voice_too_long"
        assert bed.testbed.media_storage.files == {}


class TestRealRecordings:
    @pytest.mark.parametrize(
        ("name", "declared"),
        [
            ("chromium.webm", "audio/webm;codecs=opus"),
            ("chromium.mp4", "audio/mp4;codecs=opus"),
            ("ffmpeg.ogg", "audio/ogg;codecs=opus"),
            ("ffmpeg.m4a", "audio/mp4"),
            ("ffmpeg_fragmented.m4a", "audio/mp4"),
        ],
    )
    def test_recordings_of_real_encoders_are_taken(
        self, name: str, declared: str
    ) -> None:
        bed = WidgetUploadBed()

        response = bed.upload((RECORDINGS / name).read_bytes(), declared)

        assert response.status_code == 201, response.text
        assert response.json()["duration_seconds"] == 2

    def test_a_chromium_recording_is_transcribed_and_metered(self) -> None:
        bed = WidgetUploadBed()
        testbed = bed.testbed
        recording = (RECORDINGS / "chromium.webm").read_bytes()
        voice_id = bed.uploaded_id(recording, "audio/webm;codecs=opus")

        assert bed.send([voice_id]).status_code == 202
        testbed.run_worker()

        [message] = testbed.pipeline.messages
        [voice] = message.attachments
        assert voice.kind is AttachmentKind.AUDIO
        assert voice.transcript is not None
        assert voice.duration_seconds == 2
        [usage] = transcription_usage(testbed, bed.business.id)
        assert int(usage.quantity) == 2

    def test_the_worker_does_not_trust_the_uploads_stored_length(self) -> None:
        bed = WidgetUploadBed()
        testbed = bed.testbed
        voice_id = bed.uploaded_id(webm_recording(40), "audio/webm")
        upload = bed.stored_upload(voice_id)
        # As if the upload had been measured wrong: the worker measures again.
        upload.duration_seconds = AudioDurationSeconds(1)
        testbed.widget_upload_repo.save(upload)

        assert bed.send([voice_id]).status_code == 202
        testbed.run_worker()

        [message] = testbed.pipeline.messages
        [voice] = message.attachments
        assert voice.duration_seconds == 40
        [usage] = transcription_usage(testbed, bed.business.id)
        assert int(usage.quantity) == 40
