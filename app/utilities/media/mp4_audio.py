"""
How long an MP4 (M4A) recording is, read from its boxes without decoding
it: Safari records AAC in MP4, Chromium can record Opus in it.

The movie and track headers, the edit lists, the time-to-sample tables
and the fragments' runs all state durations, and the writer chose every
one of them; the samples are what a decoder plays (an AAC frame is 1024
samples of its core rate, an Opus packet says its own length). The length
is the largest of all of them, so no single forged header makes a long
recording pass as a short one. Only a file whose every track is sound, in
AAC or Opus, counts.
"""

import math
import struct

from app.utilities.media.mp4_boxes import (
    Mp4Box,
    Mp4StructureError,
    child_boxes,
    full_box_fields,
    only_child,
    read_fields,
    read_versioned_fields,
    required_child,
    top_level_boxes,
)
from app.utilities.media.mp4_fragments import read_fragment, read_track_defaults
from app.utilities.media.mp4_sample_tables import read_sound_track
from app.utilities.media.mp4_sound_track import SoundTrack

FILE_TYPE: bytes = b"ftyp"
MOVIE: bytes = b"moov"
MOVIE_FRAGMENT: bytes = b"moof"
MOVIE_HEADER_LAYOUTS: dict[int, str] = {0: ">8xII", 1: ">16xIQ"}
FRAGMENT_DURATION_LAYOUTS: dict[int, str] = {0: ">I", 1: ">Q"}


def read_mp4_audio_seconds(content: bytes) -> int | None:
    """
    Whole seconds (rounded up) of an MP4 recording of AAC or Opus sound
    tracks; None for anything else (a video track, another codec, boxes or
    tables that do not add up).
    """

    try:
        seconds: float = measure_mp4_audio(content)
    except IndexError, KeyError, struct.error, ValueError:
        return None

    if seconds < 0 or not math.isfinite(seconds):
        return None

    return math.ceil(seconds)


def measure_mp4_audio(content: bytes) -> float:
    """
    The longest of every duration the file states and of its tracks' samples.

    Raises:
        Mp4StructureError: not a sound-only MP4 this reader walks.
    """

    boxes: list[Mp4Box] = top_level_boxes(content)
    movies: list[Mp4Box] = [box for box in boxes if box.kind == MOVIE]
    if not boxes or boxes[0].kind != FILE_TYPE or len(movies) != 1:
        raise Mp4StructureError("Not one MP4 movie.")

    movie: Mp4Box = movies[0]
    timescale, duration = read_versioned_fields(
        content, required_child(content, movie, b"mvhd"), MOVIE_HEADER_LAYOUTS
    )
    if timescale <= 0:
        raise Mp4StructureError("The movie's timescale is zero.")

    tracks: dict[int, SoundTrack] = {}
    for track_box in child_boxes(content, movie, b"trak"):
        track: SoundTrack = read_sound_track(content, track_box, timescale)
        if track.track_id in tracks:
            raise Mp4StructureError("Two tracks share an id.")
        tracks[track.track_id] = track
    if not tracks:
        raise Mp4StructureError("The movie has no track.")

    defaults = read_track_defaults(content, movie)
    for fragment in (box for box in boxes if box.kind == MOVIE_FRAGMENT):
        read_fragment(content, fragment, tracks, defaults)

    claimed: list[float] = [
        duration / timescale,
        fragment_duration(content, movie) / timescale,
    ]
    return max([*claimed, *(track.longest_seconds() for track in tracks.values())])


def fragment_duration(content: bytes, movie: Mp4Box) -> int:
    """The whole fragmented movie's duration its extends header states."""

    extends: Mp4Box | None = only_child(content, movie, b"mvex")
    header: Mp4Box | None = (
        None if extends is None else only_child(content, extends, b"mehd")
    )
    if header is None:
        return 0

    version, _, at = full_box_fields(content, header)
    if version not in FRAGMENT_DURATION_LAYOUTS:
        raise Mp4StructureError("An unknown movie extends header version.")

    (total,) = read_fields(content, header, FRAGMENT_DURATION_LAYOUTS[version], at)
    return total
