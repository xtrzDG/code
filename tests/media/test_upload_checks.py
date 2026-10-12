"""
The byte-level checks of a visitor's upload: photos rebuilt without their
metadata (orientation kept), malformed files refused, recordings measured
from their containers and refused when they hold video.
"""

import struct

import pytest

from app.schemas.exceptions.media_errors import MalformedMediaFileError
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.strings import DeclaredUploadType
from app.utilities.media.exif_orientation import (
    orientation_only_exif,
    read_exif_orientation,
)
from app.utilities.media.jpeg_metadata import strip_jpeg_metadata
from app.utilities.media.png_metadata import strip_png_metadata
from app.utilities.media.upload_checks import (
    measure_voice_note,
    read_declared_type,
    upload_kind_of,
)
from app.utilities.media.webm_audio import read_webm_audio_seconds
from app.utilities.media.webp_metadata import strip_webp_metadata
from tests.media.media_fakes import ogg_opus_bytes
from tests.media.upload_files import (
    COMMENT_TEXT,
    DEVICE_TEXT,
    GPS_TEXT,
    UNKNOWN_SIZE,
    VIDEO_TRACK,
    ebml,
    exif_payload,
    jpeg_photo,
    mp4_recording,
    ogg_theora_bytes,
    png_chunk,
    png_photo,
    uint,
    webm_recording,
    webp_photo,
)


class TestJpeg:
    def test_metadata_and_appended_pictures_are_dropped(self) -> None:
        trailer = b"\xff\xd8\xff\xe1 preview Exif " + GPS_TEXT + b"\xff\xd9"

        stripped = strip_jpeg_metadata(jpeg_photo(orientation=6, trailer=trailer))

        for personal in (GPS_TEXT, DEVICE_TEXT, COMMENT_TEXT, b"xmpmeta"):
            assert personal not in stripped
        assert stripped.startswith(b"\xff\xd8\xff\xe0")
        assert stripped.endswith(b"\xff\xd9") and b"preview" not in stripped
        # The tables, frame, scan and its stuffed bytes survive untouched.
        assert b"\x12\x34\xff\x00\x56\xff\xd0\x78\xff\xd9" in stripped
        assert bytes(range(1, 65)) in stripped

    def test_only_the_orientation_of_exif_is_kept(self) -> None:
        stripped = strip_jpeg_metadata(jpeg_photo(orientation=8))
        upright = strip_jpeg_metadata(jpeg_photo(orientation=1))
        without = strip_jpeg_metadata(jpeg_photo(orientation=None))

        exif_at = stripped.index(b"Exif\x00\x00")
        assert read_exif_orientation(stripped[exif_at:]) == 8
        assert b"Exif" not in upright and b"Exif" not in without

    def test_the_orientation_block_holds_one_tag(self) -> None:
        block = orientation_only_exif(3)

        assert read_exif_orientation(block) == 3
        assert read_exif_orientation(exif_payload(5)) == 5
        assert read_exif_orientation(exif_payload(None)) is None
        assert read_exif_orientation(b"Exif\x00\x00XX" + bytes(8)) is None

    @pytest.mark.parametrize(
        "content",
        [
            b"\x89PNG" + bytes(20),
            b"\xff\xd8\xff\xe0\x00\x40JFIF",
            b"\xff\xd8\xff\xda\x00\x08" + bytes(6) + b"\x12\x34",
            b"\xff\xd8\x00\x00",
        ],
    )
    def test_a_file_whose_segments_do_not_add_up_is_refused(
        self, content: bytes
    ) -> None:
        with pytest.raises(MalformedMediaFileError):
            strip_jpeg_metadata(content)


class TestPngAndWebp:
    def test_png_keeps_only_drawing_chunks(self) -> None:
        stripped = strip_png_metadata(png_photo() + b"appended " + GPS_TEXT)

        assert stripped.startswith(b"\x89PNG\r\n\x1a\n")
        for dropped in (b"tEXt", b"eXIf", b"tIME", COMMENT_TEXT, GPS_TEXT):
            assert dropped not in stripped
        assert b"IHDR" in stripped and b"IDAT" in stripped
        assert stripped.endswith(png_chunk(b"IEND", b""))

    def test_png_with_a_broken_checksum_is_refused(self) -> None:
        photo = bytearray(png_photo())
        photo[-5] ^= 0xFF

        with pytest.raises(MalformedMediaFileError):
            strip_png_metadata(bytes(photo))

    def test_webp_loses_exif_xmp_and_their_flags(self) -> None:
        stripped = strip_webp_metadata(webp_photo())

        assert b"EXIF" not in stripped and b"XMP " not in stripped
        assert GPS_TEXT not in stripped
        assert stripped[20] & (0x08 | 0x04) == 0
        (riff_size,) = struct.unpack_from("<I", stripped, 4)
        assert riff_size == len(stripped) - 8

    def test_webp_without_a_frame_or_cut_short_is_refused(self) -> None:
        photo = webp_photo()
        frameless = photo.replace(b"VP8L", b"JUNK")

        for broken in (frameless, photo[:30], b"RIFF\x00\x00\x00\x00WEBQ"):
            with pytest.raises(MalformedMediaFileError):
                strip_webp_metadata(broken)


class TestRecordings:
    def test_webm_length_from_its_blocks_or_its_header(self) -> None:
        assert read_webm_audio_seconds(webm_recording(8)) == 8
        assert read_webm_audio_seconds(webm_recording(37)) == 37
        assert read_webm_audio_seconds(webm_recording(12, header_duration=True)) == 12

    def test_webm_with_video_or_of_another_kind_is_not_a_voice_note(self) -> None:
        with_video = webm_recording(5, track_types=(2, VIDEO_TRACK))
        matroska = webm_recording(5, doc_type=b"matroska")
        no_tracks = ebml(0x1A45DFA3, ebml(0x4282, b"webm")) + uint(0x18538067)

        assert read_webm_audio_seconds(with_video) is None
        assert read_webm_audio_seconds(matroska) is None
        assert read_webm_audio_seconds(no_tracks + UNKNOWN_SIZE) is None
        assert read_webm_audio_seconds(b"\x1a\x45\xdf\xa3\x00") is None

    def test_a_recording_cut_at_its_end_still_counts(self) -> None:
        recording = webm_recording(6)

        assert read_webm_audio_seconds(recording[:-4]) in (0, 6)

    def test_every_browser_container_is_measured_and_video_refused(self) -> None:
        webm = MessageMediaType("audio/webm")
        ogg = MessageMediaType("audio/ogg")
        mp4 = MessageMediaType("audio/mp4")

        assert measure_voice_note(webm_recording(4), webm) == 4
        assert measure_voice_note(ogg_opus_bytes(seconds=3), ogg) == 3
        assert measure_voice_note(mp4_recording(11), mp4) == 11
        assert measure_voice_note(ogg_theora_bytes(), ogg) is None
        assert measure_voice_note(mp4_recording(5, (b"vide",)), mp4) is None
        assert measure_voice_note(mp4_recording(5, (b"soun", b"vide")), mp4) is None


class TestDeclaredTypes:
    def test_parameters_and_case_are_ignored(self) -> None:
        assert read_declared_type(DeclaredUploadType("Audio/WebM; codecs=opus")) == (
            "audio/webm"
        )
        assert read_declared_type(DeclaredUploadType(";")) is None
        assert read_declared_type(None) is None

    def test_only_photos_and_voice_notes_have_a_kind(self) -> None:
        kinds = [
            upload_kind_of(kind)
            for kind in ("image/jpeg", "image/webp", "audio/ogg", "image/gif", None)
        ]

        assert [kind.value if kind else None for kind in kinds] == [
            "image",
            "image",
            "audio",
            None,
            None,
        ]
