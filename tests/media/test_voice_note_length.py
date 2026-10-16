"""
A voice note's length is measured from the audio itself as well as from
what its container claims, so a forged header, forged block times, a
forged last page or forged sample tables never make a long recording pass
as a short one (each case below measured 1 s before the readers counted
the packets and frames).
"""

import struct
from pathlib import Path

import pytest

from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.utilities.media.media_sniffing import sniff_media_type
from app.utilities.media.mp4_boxes import Mp4Box, Mp4StructureError, only_child
from app.utilities.media.opus_packets import opus_packet_samples
from app.utilities.media.voice_note_length import (
    measure_audio_seconds,
    measure_voice_note,
)
from tests.media.media_fakes import ogg_opus_bytes
from tests.media.mp4_files import (
    box,
    edit_list,
    fragmented_mp4_recording,
    mp4_recording,
)
from tests.media.recording_files import (
    OVERSIZED_VOID,
    ebml,
    ogg_opus_recording,
    ogg_page,
    webm_header,
    webm_opus_stream,
    webm_recording,
    with_element_before_second_cluster,
)

WEBM: MessageMediaType = MessageMediaType("audio/webm")
OGG: MessageMediaType = MessageMediaType("audio/ogg")
MP4: MessageMediaType = MessageMediaType("audio/mp4")
RECORDINGS: Path = Path(__file__).parent / "recordings"
TEN_MINUTES: int = 600


class TestOpusPackets:
    @pytest.mark.parametrize(
        ("packet", "samples"),
        [
            (b"\xf8", 960),  # CELT 20 ms, one frame
            (b"\xf9\x00", 1920),  # two frames of the same size
            (b"\xfb\x03", 2880),  # three frames (code 3)
            (b"\x18", 2880),  # SILK 60 ms
            (b"\x78", 960),  # Hybrid 20 ms
            (b"\x83\x30", 5760),  # 48 frames of 2.5 ms: the 120 ms most
        ],
    )
    def test_the_toc_byte_tells_the_length(self, packet: bytes, samples: int) -> None:
        assert opus_packet_samples(packet) == samples

    @pytest.mark.parametrize("packet", [b"", b"\xfb", b"\xfb\x00", b"\x1b\x03"])
    def test_bytes_that_are_no_opus_packet_have_no_length(self, packet: bytes) -> None:
        assert opus_packet_samples(packet) is None


class TestForgedWebm:
    def test_a_short_header_duration_does_not_hide_the_blocks(self) -> None:
        recording = webm_recording(TEN_MINUTES, header_duration=True).replace(
            struct.pack(">d", TEN_MINUTES * 1000.0), struct.pack(">d", 1000.0)
        )

        assert measure_voice_note(recording, WEBM) == TEN_MINUTES

    def test_squeezed_block_times_do_not_hide_the_packets(self) -> None:
        # 10 000 packets of 60 ms, every block at 0 ms, the header saying 1 s.
        squeezed = webm_opus_stream(10_000, spacing_ms=0, duration_ms=1000.0)

        assert measure_voice_note(squeezed, WEBM) == TEN_MINUTES

    def test_an_element_running_past_the_end_does_not_cut_the_count(self) -> None:
        # Ten minutes, the header saying 1 s, an oversized Void after the
        # first cluster: the count stopped there at 10 s while a decoder
        # resyncs at the next cluster and plays all ten minutes.
        recording = webm_recording(TEN_MINUTES, header_duration=True).replace(
            struct.pack(">d", TEN_MINUTES * 1000.0), struct.pack(">d", 1000.0)
        )
        forged = with_element_before_second_cluster(recording, OVERSIZED_VOID)

        assert measure_voice_note(forged, WEBM) is None
        assert measure_audio_seconds(forged, WEBM) is None

    def test_honest_recordings_keep_their_length(self) -> None:
        assert measure_voice_note(webm_opus_stream(1000), WEBM) == 60
        assert measure_voice_note(webm_recording(37), WEBM) == 37
        assert measure_voice_note(webm_recording(12, header_duration=True), WEBM) == 12

    def test_what_a_decoder_would_read_differently_is_refused(self) -> None:
        laced = webm_opus_stream(10).replace(b"\x80\xfb\x03", b"\x82\xfb\x03", 1)
        not_opus = webm_opus_stream(10).replace(b"A_OPUS", b"A_VORB")
        plain_header = webm_header()
        compressed = (
            webm_header(track_extra=ebml(0x6D80, b""))
            + webm_recording(5)[len(plain_header) :]
        )
        no_packet = webm_opus_stream(10, packet=b"")

        for refused in (laced, not_opus, compressed, no_packet):
            assert measure_voice_note(refused, WEBM) is None


class TestForgedOgg:
    def test_a_short_last_granule_does_not_hide_the_packets(self) -> None:
        forged = ogg_opus_recording(TEN_MINUTES, last_granule=48_000)

        assert measure_voice_note(forged, OGG) == TEN_MINUTES

    def test_a_page_appended_after_the_end_is_refused(self) -> None:
        recording = ogg_opus_recording(TEN_MINUTES)
        appended = ogg_page([b"\xf8"], 48_000, 999)
        raw_tail = b"OggS\x00\x04" + struct.pack("<q", 48_000) + bytes(16)

        assert measure_voice_note(recording + appended, OGG) is None
        assert measure_voice_note(recording + raw_tail, OGG) is None

    def test_broken_or_chained_streams_are_refused(self) -> None:
        recording = bytearray(ogg_opus_recording(3))
        recording[-1] ^= 0xFF
        chained = ogg_opus_recording(2) + ogg_opus_recording(2, serial=7)
        cut = ogg_opus_recording(2)[:-1]

        assert measure_voice_note(bytes(recording), OGG) is None
        assert measure_voice_note(chained, OGG) is None
        assert measure_voice_note(cut, OGG) is None
        # A platform's stand-in without real pages is no browser recording.
        assert measure_voice_note(ogg_opus_bytes(seconds=3), OGG) is None

    def test_an_honest_recording_keeps_its_length(self) -> None:
        assert measure_voice_note(ogg_opus_recording(5), OGG) == 5
        assert measure_voice_note(ogg_opus_recording(59, packets_per_page=7), OGG) == 59


class TestForgedMp4:
    def test_short_headers_and_tables_do_not_hide_the_frames(self) -> None:
        aac = mp4_recording(TEN_MINUTES, claimed_seconds=1)
        opus = mp4_recording(TEN_MINUTES, codec="opus", claimed_seconds=1)

        assert measure_voice_note(aac, MP4) == TEN_MINUTES
        assert measure_voice_note(opus, MP4) == TEN_MINUTES

    def test_short_fragment_runs_do_not_hide_the_packets(self) -> None:
        opus = fragmented_mp4_recording(TEN_MINUTES, claimed_seconds=1)
        aac = fragmented_mp4_recording(TEN_MINUTES, codec="aac", claimed_seconds=1)

        assert measure_voice_note(opus, MP4) == TEN_MINUTES
        assert measure_voice_note(aac, MP4) == TEN_MINUTES

    def test_an_edit_list_that_plays_longer_counts(self) -> None:
        repeated = mp4_recording(1, edits=edit_list(*[48_000] * TEN_MINUTES))
        silence = mp4_recording(1, edits=edit_list(48_000 * TEN_MINUTES))

        assert measure_voice_note(repeated, MP4) == TEN_MINUTES
        assert measure_voice_note(silence, MP4) == TEN_MINUTES

    def test_other_codecs_tracks_and_broken_tables_are_refused(self) -> None:
        recording = mp4_recording(5)
        mislabelled = recording.replace(b"stco", b"co64", 1)

        assert measure_voice_note(mp4_recording(5, codec="mp3"), MP4) is None
        assert measure_voice_note(mp4_recording(5, (b"soun", b"vide")), MP4) is None
        assert measure_voice_note(mislabelled, MP4) is None
        assert measure_voice_note(recording[:-40], MP4) is None

    def test_a_box_read_once_may_not_appear_twice(self) -> None:
        tables = box(b"stbl", box(b"stsz", bytes(8)) + box(b"stsz", bytes(8)))
        parent = Mp4Box(kind=b"stbl", start=0, data_start=8, end=len(tables))

        with pytest.raises(Mp4StructureError):
            only_child(tables, parent, b"stsz")

    def test_honest_recordings_keep_their_length(self) -> None:
        assert measure_voice_note(mp4_recording(12), MP4) == 12
        assert measure_voice_note(fragmented_mp4_recording(7), MP4) == 7


class TestRealRecordings:
    @pytest.mark.parametrize(
        "name",
        [
            "chromium.webm",
            "chromium.mp4",
            "ffmpeg.ogg",
            "ffmpeg.m4a",
            "ffmpeg_fragmented.m4a",
        ],
    )
    def test_recordings_of_real_encoders_are_measured(self, name: str) -> None:
        # 1.5 s of a tone each (MediaRecorder in Chromium, ffmpeg's encoders).
        content = (RECORDINGS / name).read_bytes()
        media_type = sniff_media_type(content)

        assert media_type is not None
        assert measure_voice_note(content, media_type) == 2

    def test_the_worker_takes_the_longest_reading(self) -> None:
        # A platform's Ogg without real pages: only the container's word.
        assert measure_audio_seconds(ogg_opus_bytes(seconds=9), OGG) == 9
        assert measure_audio_seconds(ogg_opus_recording(4), OGG) == 4
        assert measure_audio_seconds(b"OggS" + bytes(8), OGG) is None
        assert measure_audio_seconds(webm_opus_stream(500), WEBM) == 30
