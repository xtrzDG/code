"""
What a WebM recording is and how long it lasts, read from its EBML
structure without decoding it.

A browser's MediaRecorder writes WebM as it records: the segment and its
clusters have an unknown size, so the segment, its clusters and block
groups are walked as one stream. The header's duration and the blocks'
times are claims the writer made, so the length is the largest of them
and of what the blocks hold: each block is one Opus packet, which says
how long it plays (`opus_packets`). Only a WebM file whose every track is
Opus audio counts: a video, another codec, compressed or laced blocks, or
a Matroska file of another kind, is not a voice note. Nor is a file cut
short or with an element running past its end: a decoder resyncs at the
next cluster and plays on, where a count that stopped there falls short.
"""

import math
import struct
from dataclasses import dataclass, field

from app.utilities.media.ebml_elements import (
    WebmStructureError,
    read_id,
    read_size,
)
from app.utilities.media.opus_packets import OPUS_SAMPLE_RATE, opus_packet_samples

EBML_HEADER: int = 0x1A45DFA3
DOC_TYPE: int = 0x4282
SEGMENT: int = 0x18538067
INFO: int = 0x1549A966
TIMECODE_SCALE: int = 0x2AD7B1
DURATION: int = 0x4489
TRACKS: int = 0x1654AE6B
TRACK_ENTRY: int = 0xAE
TRACK_TYPE: int = 0x83
CODEC_ID: int = 0x86
CONTENT_ENCODINGS: int = 0x6D80
CLUSTER: int = 0x1F43B675
CLUSTER_TIMECODE: int = 0xE7
BLOCK_GROUP: int = 0xA0
BLOCK: int = 0xA1
SIMPLE_BLOCK: int = 0xA3
# Read as part of the stream around them (an unknown size is allowed).
STREAM_CONTAINERS: frozenset[int] = frozenset({SEGMENT, CLUSTER, BLOCK_GROUP})
AUDIO_TRACK: int = 2
OPUS_CODEC: bytes = b"A_OPUS"
WEBM_DOC_TYPE: bytes = b"webm"
NANOSECONDS_PER_SECOND: int = 1_000_000_000
DEFAULT_TIMECODE_SCALE: int = 1_000_000
FLOAT_FORMATS: dict[int, str] = {4: ">f", 8: ">d"}
# A block's flags byte: bits 1-2 tell its lacing (several frames in one).
LACING_BITS: int = 0x06
# The block header after its track number: a 16-bit time offset and flags.
BLOCK_HEADER_BYTES: int = 3
# The TOC byte and, for a packet of many frames, its frame count.
PACKET_HEAD_BYTES: int = 2
# A voice note of an hour has some 180,000 blocks (20 ms Opus frames); a
# file of far more elements, or nested deeper than a real header, is not
# one, and is not walked to its end.
MOST_ELEMENTS: int = 500_000
DEEPEST_HEADER: int = 4


@dataclass
class WebmReading:
    """What the walk found: the header's facts, the blocks' times and length."""

    doc_type: bytes = b""
    timecode_scale: int = DEFAULT_TIMECODE_SCALE
    duration_ticks: float | None = None
    track_types: list[int] = field(default_factory=list[int])
    codec_ids: list[bytes] = field(default_factory=list[bytes])
    cluster_timecode: int = 0
    latest_ticks: int = 0
    packet_samples: int = 0
    element_count: int = 0

    def count_element(self) -> None:
        self.element_count += 1
        if self.element_count > MOST_ELEMENTS:
            raise WebmStructureError("Too many elements for a voice note.")

    def is_opus_audio(self) -> bool:
        """WebM whose every track (one at least) is Opus audio."""

        return (
            self.doc_type == WEBM_DOC_TYPE
            and bool(self.track_types)
            and all(kind == AUDIO_TRACK for kind in self.track_types)
            and self.codec_ids == [OPUS_CODEC] * len(self.track_types)
        )


def read_webm_audio_seconds(content: bytes) -> int | None:
    """
    Whole seconds (rounded up) of a WebM file of Opus audio tracks: the
    longest of its header's duration, its latest block's time and its
    packets' length. None for anything else (another kind of file, a
    video track, a structure that does not parse).
    """

    reading = WebmReading()
    try:
        walk(content, 0, len(content), reading)
    except IndexError, KeyError, struct.error, ValueError:
        return None

    if not reading.is_opus_audio():
        return None

    scale: float = reading.timecode_scale / NANOSECONDS_PER_SECOND
    claims: list[float] = [
        reading.latest_ticks * scale,
        reading.packet_samples / OPUS_SAMPLE_RATE,
    ]
    if reading.duration_ticks is not None:
        claims.append(reading.duration_ticks * scale)

    if any(claim < 0 or not math.isfinite(claim) for claim in claims):
        return None

    return math.ceil(max(claims))


def walk(content: bytes, start: int, end: int, reading: WebmReading) -> None:
    """Read the elements from `start` to `end`, the stream containers inline."""

    position: int = start
    while position < end:
        reading.count_element()
        element_id, position = read_id(content, position)
        size, position = read_size(content, position)
        if element_id in STREAM_CONTAINERS:
            continue

        if size is None:
            raise WebmStructureError(
                "Only a segment, a cluster or a block group grows."
            )

        data_end: int = position + size
        if data_end > end:
            # MediaRecorder's Blob is whole. An element running past the end
            # is a forgery a decoder skips by resyncing at the next cluster,
            # whose audio would play but not be counted here.
            raise WebmStructureError("An element runs past the end of the file.")

        read_element(content, element_id, position, data_end, reading, 0)
        position = data_end


def read_element(
    content: bytes,
    element_id: int,
    start: int,
    end: int,
    reading: WebmReading,
    depth: int,
) -> None:
    if element_id in (EBML_HEADER, INFO, TRACKS, TRACK_ENTRY):
        walk_children(content, start, end, reading, depth + 1)
    elif element_id == DOC_TYPE:
        reading.doc_type = content[start:end].rstrip(b"\x00")
    elif element_id == TIMECODE_SCALE:
        scale: int = int.from_bytes(content[start:end], "big")
        reading.timecode_scale = scale or DEFAULT_TIMECODE_SCALE
    elif element_id == DURATION:
        data: bytes = content[start:end]
        (reading.duration_ticks,) = struct.unpack(FLOAT_FORMATS[len(data)], data)
    elif element_id == TRACK_TYPE:
        reading.track_types.append(int.from_bytes(content[start:end], "big"))
    elif element_id == CODEC_ID:
        reading.codec_ids.append(content[start:end].rstrip(b"\x00"))
    elif element_id == CONTENT_ENCODINGS:
        # Compressed (header-stripped) or encrypted frames are not read as sent.
        raise WebmStructureError("A track's frames are encoded.")
    elif element_id == CLUSTER_TIMECODE:
        reading.cluster_timecode = int.from_bytes(content[start:end], "big")
    elif element_id in (SIMPLE_BLOCK, BLOCK):
        read_block(content, start, end, reading)


def read_block(content: bytes, start: int, end: int, reading: WebmReading) -> None:
    """A block's time (its cluster's plus its offset) and its packet's length."""

    _, header_at = read_size(content, start)
    frame_at: int = header_at + BLOCK_HEADER_BYTES
    if frame_at >= end:
        raise WebmStructureError("A block holds no frame.")

    (offset,) = struct.unpack_from(">h", content, header_at)
    if content[header_at + 2] & LACING_BITS:
        raise WebmStructureError("Laced blocks are not a browser's recording.")

    samples: int | None = opus_packet_samples(
        content[frame_at : min(end, frame_at + PACKET_HEAD_BYTES)]
    )
    if samples is None:
        raise WebmStructureError("A block is not an Opus packet.")

    reading.packet_samples += samples
    reading.latest_ticks = max(reading.latest_ticks, reading.cluster_timecode + offset)


def walk_children(
    content: bytes, start: int, end: int, reading: WebmReading, depth: int
) -> None:
    """The children of a sized element (header, info, tracks, a track)."""

    if depth > DEEPEST_HEADER:
        raise WebmStructureError("Header elements nest deeper than WebM's.")

    position: int = start
    while position < end:
        reading.count_element()
        element_id, position = read_id(content, position)
        size, position = read_size(content, position)
        if size is None or position + size > end:
            raise WebmStructureError("A header element runs past its parent.")

        read_element(content, element_id, position, position + size, reading, depth)
        position += size
