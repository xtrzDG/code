"""
The small rules behind customer media: what a file really is, how long a
voice note lasts, where it is kept, what transcription costs, how settings
are read and how attachments read for people and for the model.
"""

import struct
from uuid import NAMESPACE_URL, uuid5

import pytest

from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.domain.message_media import MessageAttachment, SharedLocation
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.schemas.typings.media.constrained_floats import Latitude, Longitude
from app.schemas.typings.media.constrained_integers import AudioDurationSeconds
from app.schemas.typings.media.constrained_strings import (
    MessageMediaType,
    TranscriptionModelId,
)
from app.schemas.typings.media.strings import (
    LocationAddress,
    LocationName,
    MediaStoragePath,
    TranscribedVoiceText,
)
from app.utilities.media.attachment_texts import (
    describe_message_for_model,
    has_readable_content,
    map_link,
    readable_message_text,
)
from app.utilities.media.audio_duration import read_audio_duration_seconds
from app.utilities.media.media_paths import (
    derive_message_media_id,
    media_storage_path,
    media_type_of_extension,
)
from app.utilities.media.media_sniffing import kind_of_media_type, sniff_media_type
from app.utilities.media.transcription_pricing import transcription_cost
from tests.channels.channels_settings import build_settings
from tests.media.media_fakes import jpeg_bytes, ogg_opus_bytes, png_bytes

PADDING: bytes = bytes(16)


def event_id(name: str) -> InboundEventId:
    return InboundEventId(uuid5(NAMESPACE_URL, name))


def ogg_vorbis_bytes(rate: int, samples: int) -> bytes:
    head = b"OggS" + bytes(24) + b"\x01vorbis" + bytes(5) + struct.pack("<I", rate)
    last = b"OggS" + b"\x00\x04" + struct.pack("<q", samples) + bytes(16)
    return head + bytes(64) + last


def mp4_bytes(version: int, timescale: int, duration: int) -> bytes:
    # After the version byte: flags and the creation and change times.
    if version == 1:
        body = bytes(19) + struct.pack(">IQ", timescale, duration)
    else:
        body = bytes(11) + struct.pack(">II", timescale, duration)
    return bytes(4) + b"ftypM4A " + bytes(8) + b"mvhd" + bytes([version]) + body


def wav_bytes(byte_rate: int, data_size: int) -> bytes:
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, byte_rate, 1, 8)
    return b"RIFF" + bytes(4) + b"WAVE" + fmt + b"data" + struct.pack("<I", data_size)


class TestSniffing:
    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (jpeg_bytes(), "image/jpeg"),
            (png_bytes(), "image/png"),
            (b"RIFF\x00\x00\x00\x00WEBPVP8 " + PADDING, "image/webp"),
            (b"GIF89a" + PADDING, "image/gif"),
            (ogg_opus_bytes(), "audio/ogg"),
            (b"ID3\x04" + PADDING, "audio/mpeg"),
            (b"\xff\xfb\x90\x64" + PADDING, "audio/mpeg"),
            (mp4_bytes(0, 1000, 7000), "audio/mp4"),
            (b"#!AMR\n" + PADDING, "audio/amr"),
            (wav_bytes(8000, 8000), "audio/wav"),
            (b"\x1a\x45\xdf\xa3" + PADDING, "audio/webm"),
        ],
    )
    def test_audio_and_pictures_are_recognized(
        self, content: bytes, expected: str
    ) -> None:
        assert sniff_media_type(content) == expected

    @pytest.mark.parametrize(
        "content",
        [
            b"<!doctype html><script>",
            b"<svg xmlns='http://www.w3.org/2000/svg'/>",
            b"%PDF-1.7\n" + PADDING,
            b"PK\x03\x04" + PADDING,
            b"short",
        ],
    )
    def test_anything_else_is_refused(self, content: bytes) -> None:
        assert sniff_media_type(content) is None

    def test_the_kind_follows_the_type(self) -> None:
        assert kind_of_media_type(MessageMediaType("image/png")) is AttachmentKind.IMAGE
        assert kind_of_media_type(MessageMediaType("audio/ogg")) is AttachmentKind.AUDIO


class TestAudioDuration:
    def test_containers_tell_their_length_rounded_up(self) -> None:
        assert read_audio_duration_seconds(ogg_opus_bytes(seconds=7)) == 7
        assert read_audio_duration_seconds(ogg_vorbis_bytes(44_100, 44_100 * 3)) == 3
        assert read_audio_duration_seconds(mp4_bytes(0, 1000, 7_200)) == 8
        assert read_audio_duration_seconds(mp4_bytes(1, 600, 600 * 12)) == 12
        assert read_audio_duration_seconds(wav_bytes(8000, 8000 * 5)) == 5

    @pytest.mark.parametrize(
        "content",
        [
            b"OggS" + bytes(60),
            ogg_vorbis_bytes(0, 1000),
            ogg_vorbis_bytes(44_100, -5),
            mp4_bytes(0, 0, 1000),
            bytes(4) + b"ftypM4A " + b"mvhd",
            bytes(4) + b"ftyp" + b"mvhd" + bytes(2),
            b"RIFF" + bytes(4) + b"WAVE" + b"fmt " + bytes(4),
            b"RIFF" + bytes(4) + b"WAVE",
            wav_bytes(0, 100),
            jpeg_bytes(),
        ],
    )
    def test_what_the_readers_do_not_understand_has_no_length(
        self, content: bytes
    ) -> None:
        assert read_audio_duration_seconds(content) is None


class TestPaths:
    def test_the_same_attachment_of_the_same_event_keeps_one_id(self) -> None:
        event = event_id("event-1")
        assert derive_message_media_id(event, 0) == derive_message_media_id(event, 0)
        assert derive_message_media_id(event, 0) != derive_message_media_id(event, 1)
        assert derive_message_media_id(event, 0) != derive_message_media_id(
            event_id("event-2"), 0
        )

    def test_files_are_kept_per_business_with_the_extension_of_their_type(
        self,
    ) -> None:
        business_id = BusinessId()
        media_id = derive_message_media_id(event_id("event-3"), 0)

        path = media_storage_path(business_id, media_id, MessageMediaType("audio/ogg"))
        unknown = media_storage_path(
            business_id, media_id, MessageMediaType("audio/x-unknown")
        )

        assert path == f"message-media/{business_id}/{media_id}.ogg"
        assert str(unknown).endswith(".bin")
        assert media_type_of_extension("note.OGG") == "audio/ogg"
        assert media_type_of_extension("photo.jpg") == "image/jpeg"
        assert media_type_of_extension("archive") is None
        assert media_type_of_extension("x.bin") is None


def test_transcription_is_priced_per_second_by_model() -> None:
    seconds = AudioDurationSeconds(60)
    mini = transcription_cost(TranscriptionModelId("gpt-4o-mini-transcribe"), seconds)
    full = transcription_cost(TranscriptionModelId("gpt-4o-transcribe"), seconds)
    unknown = transcription_cost(TranscriptionModelId("gpt-transcribe"), seconds)

    assert (int(mini), int(full), int(unknown)) == (3000, 6000, 6000)


class TestSettings:
    def test_defaults_fit_voice_notes_and_photos(self) -> None:
        media = build_settings().media

        assert media.transcription_model_id == "gpt-4o-transcribe"
        assert int(media.max_voice_bytes) == 16 * 1024 * 1024
        assert int(media.max_image_bytes) == 5 * 1024 * 1024
        assert int(media.max_voice_seconds) == 300

    def test_each_value_can_be_changed(self) -> None:
        media = build_settings(
            LLM_TRANSCRIBE_MODEL="gpt-4o-mini-transcribe",
            MEDIA_MAX_VOICE_BYTES="2097152",
            MEDIA_MAX_IMAGE_BYTES="1048576",
            MEDIA_MAX_VOICE_SECONDS="120",
        ).media

        assert media.transcription_model_id == "gpt-4o-mini-transcribe"
        assert int(media.max_voice_bytes) == 2 * 1024 * 1024
        assert int(media.max_image_bytes) == 1024 * 1024
        assert int(media.max_voice_seconds) == 120

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("MEDIA_MAX_VOICE_BYTES", "100"),
            ("MEDIA_MAX_IMAGE_BYTES", str(64 * 1024 * 1024)),
            ("MEDIA_MAX_VOICE_SECONDS", "1"),
            ("MEDIA_MAX_VOICE_SECONDS", "many"),
        ],
    )
    def test_values_out_of_range_stop_the_start(self, name: str, value: str) -> None:
        with pytest.raises(ValidationFailedError, match=name):
            build_settings(**{name: value})


class TestAttachmentTexts:
    place = SharedLocation(
        latitude=Latitude(41.693438),
        longitude=Longitude(44.80152),
        name=LocationName("Freedom Square"),
        address=LocationAddress("Tbilisi"),
    )

    def test_a_place_reads_as_coordinates_names_and_a_map_link(self) -> None:
        assert map_link(self.place) == "https://maps.google.com/?q=41.693438,44.80152"
        location = MessageAttachment(kind=AttachmentKind.LOCATION, location=self.place)

        assert readable_message_text("", [location]) == (
            "41.693438, 44.80152 (Freedom Square, Tbilisi) "
            "https://maps.google.com/?q=41.693438,44.80152"
        )
        assert describe_message_for_model("I'm here", [location]).startswith(
            "[Location] 41.693438, 44.80152"
        )

    def test_the_model_reads_one_line_per_attachment_then_the_text(self) -> None:
        voice = MessageAttachment(
            kind=AttachmentKind.AUDIO, transcript=TranscribedVoiceText(" Hi there ")
        )
        silent = MessageAttachment(
            kind=AttachmentKind.AUDIO, problem=AttachmentProblem.NOT_UNDERSTOOD
        )
        photo = MessageAttachment(
            kind=AttachmentKind.IMAGE,
            storage_path=MediaStoragePath("message-media/b/p.jpg"),
            media_type=MessageMediaType("image/jpeg"),
        )
        lost_photo = MessageAttachment(
            kind=AttachmentKind.IMAGE, problem=AttachmentProblem.UNAVAILABLE
        )
        sticker = MessageAttachment(
            kind=AttachmentKind.STICKER, problem=AttachmentProblem.UNSUPPORTED_KIND
        )
        card = MessageAttachment(kind=AttachmentKind.CONTACT)
        other = MessageAttachment(kind=AttachmentKind.OTHER)

        described = describe_message_for_model(
            "Is this on the menu?",
            [voice, silent, photo, lost_photo, sticker, card, other],
        )

        assert described.split("\n\n") == [
            "[Voice message, transcribed]\nHi there",
            "[Voice message: no words could be made out]",
            "[Photo]",
            "[Photo: it could not be opened]",
            "[Sticker]",
            "[Contact card: it cannot be read]",
            "[File: it cannot be opened]",
            "Is this on the menu?",
        ]
        assert readable_message_text("Hello", [voice, photo, sticker]) == (
            "Hello\n\nHi there"
        )

    def test_something_to_answer_is_words_or_an_attachment_it_reads(self) -> None:
        sticker = MessageAttachment(
            kind=AttachmentKind.STICKER, problem=AttachmentProblem.UNSUPPORTED_KIND
        )
        voice = MessageAttachment(
            kind=AttachmentKind.AUDIO, transcript=TranscribedVoiceText("Hi")
        )

        assert has_readable_content("", [sticker]) is False
        assert has_readable_content("  ", []) is False
        assert has_readable_content("", [voice]) is True
        assert has_readable_content("Hi", [sticker]) is True
