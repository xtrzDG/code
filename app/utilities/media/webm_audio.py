"""
What a WebM recording is and how long it lasts, read from its EBML
structure without decoding it.

A browser's MediaRecorder writes WebM as it records: the segment and its
clusters have an unknown size and the header holds no duration. So the
segment, its clusters and block groups are walked as one stream, and the
length is the duration the header gives, else the latest block's time
(its cluster's timecode plus its own offset). Only a WebM file whose every
track is audio counts: a video, or a Matroska file of another kind, is
not a voice note.
"""

import math
import struct
from dataclasses import dataclass, field

EBML_HEADER: int = 0x1A45DFA3
DOC_TYPE: int = 0x4282
SEGMENT: int = 0x18538067
INFO: int = 0x1549A966
TIMECODE_SCALE: int = 0x2AD7B1
DURATION: int = 0x4489
TRACKS: int = 0x1654AE6B
TRACK_ENTRY: int = 0xAE
TRACK_TYPE: int = 0x83
CLUSTER: int = 0x1F43B675
CLUSTER_TIMECODE: int = 0xE7
BLOCK_GROUP: int = 0xA0
BLOCK: int = 0xA1
SIMPLE_BLOCK: int = 0xA3
# Read as part of the stream around them (an unknown size is allowed).
STREAM_CONTAINERS: frozenset[int] = frozenset({SEGMENT, CLUSTER, BLOCK_GROUP})
AUDIO_TRACK: int = 2
WEBM_DOC_TYPE: bytes = b"webm"
NANOSECONDS_PER_SECOND: int = 1_000_000_000
DEFAULT_TIMECODE_SCALE: int = 1_000_000
LONGEST_ID_BYTES: int = 4
LONGEST_SIZE_BYTES: int = 8
FLOAT_FORMATS: dict[int, str] = {4: ">f", 8: ">d"}
# A voice note of an hour has some 180,000 blocks (20 ms Opus frames); a
# file of far more elements, or nested deeper than a real header, is not
# one, and is not walked to its end.
MOST_ELEMENTS: int = 500_000
DEEPEST_HEADER: int = 4


class WebmStructureError(ValueError):
    """The file is not a WebM structure this reader walks."""


@dataclass
class WebmReading:
    """What the walk found: the header's facts and the latest block time."""

    doc_type: bytes = b""
    timecode_scale: int = DEFAULT_TIMECODE_SCALE
    duration_ticks: float | None = None
    track_types: list[int] = field(default_factory=list[int])
    cluster_timecode: int = 0
    latest_ticks: int = 0
    element_count: int = 0

    def count_element(self) -> None:
        self.element_count += 1
        if self.element_count > MOST_ELEMENTS:
            raise WebmStructureError("Too many elements for a voice note.")


def read_webm_audio_seconds(content: bytes) -> int | None:
    """
    Whole seconds (rounded up) of a WebM file with only audio tracks; None
    for anything else (another kind of file, a video track, a structure
    that does not parse).
    """

    reading = WebmReading()
    try:
        walk(content, 0, len(content), reading)
    except IndexError, KeyError, struct.error, ValueError:
        return None

    if reading.doc_type != WEBM_DOC_TYPE or not reading.track_types:
        return None

    if any(track_type != AUDIO_TRACK for track_type in reading.track_types):
        return None

    ticks: float = (
        reading.latest_ticks
        if reading.duration_ticks is None
        else reading.duration_ticks
    )
    seconds: float = ticks * reading.timecode_scale / NANOSECONDS_PER_SECOND
    if seconds < 0 or not math.isfinite(seconds):
        return None

    return math.ceil(seconds)


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
            # A recording cut at its very end: what came before still counts.
            return

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
    data: bytes = content[start:end]
    if element_id in (EBML_HEADER, INFO, TRACKS, TRACK_ENTRY):
        walk_children(content, start, end, reading, depth + 1)
    elif element_id == DOC_TYPE:
        reading.doc_type = data.rstrip(b"\x00")
    elif element_id == TIMECODE_SCALE:
        reading.timecode_scale = int.from_bytes(data, "big") or DEFAULT_TIMECODE_SCALE
    elif element_id == DURATION:
        (reading.duration_ticks,) = struct.unpack(FLOAT_FORMATS[len(data)], data)
    elif element_id == TRACK_TYPE:
        reading.track_types.append(int.from_bytes(data, "big"))
    elif element_id == CLUSTER_TIMECODE:
        reading.cluster_timecode = int.from_bytes(data, "big")
    elif element_id in (SIMPLE_BLOCK, BLOCK):
        _, offset_at = read_size(content, start)
        (offset,) = struct.unpack_from(">h", content, offset_at)
        reading.latest_ticks = max(
            reading.latest_ticks, reading.cluster_timecode + offset
        )


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


def read_id(content: bytes, position: int) -> tuple[int, int]:
    """An element id (its length marker kept) and the position after it."""

    length: int = vint_length(content[position], LONGEST_ID_BYTES)
    return int.from_bytes(
        content[position : position + length], "big"
    ), position + length


def read_size(content: bytes, position: int) -> tuple[int | None, int]:
    """A data size (None: unknown, all ones) and the position after it."""

    first: int = content[position]
    length: int = vint_length(first, LONGEST_SIZE_BYTES)
    value: int = first & (0xFF >> length)
    for index in range(1, length):
        value = (value << 8) | content[position + index]
    is_unknown: bool = value == (1 << (7 * length)) - 1
    return (None if is_unknown else value), position + length


def vint_length(first: int, longest: int) -> int:
    """How many bytes a variable-length integer takes, from its first byte."""

    for length in range(1, longest + 1):
        if first & (0x80 >> (length - 1)):
            return length

    raise WebmStructureError("Not an EBML variable-length integer.")
