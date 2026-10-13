"""
The samples of a fragmented MP4 recording, as browsers write it: each
movie fragment's track runs place their samples in the file and give
their durations; what a run leaves out comes from its track fragment
header, else from the track's defaults in the movie's extends box.
"""

from dataclasses import dataclass

from app.utilities.media.mp4_boxes import (
    Mp4Box,
    Mp4StructureError,
    child_boxes,
    full_box_fields,
    only_child,
    read_fields,
    required_child,
)
from app.utilities.media.mp4_sound_track import SoundTrack

# Track fragment header flags (ISO/IEC 14496-12, 8.8.7).
BASE_DATA_OFFSET_PRESENT: int = 0x000001
DESCRIPTION_INDEX_PRESENT: int = 0x000002
DEFAULT_DURATION_PRESENT: int = 0x000008
DEFAULT_SIZE_PRESENT: int = 0x000010
DEFAULT_BASE_IS_MOOF: int = 0x020000
# Track run flags (8.8.8): which fields each sample carries.
DATA_OFFSET_PRESENT: int = 0x000001
FIRST_SAMPLE_FLAGS_PRESENT: int = 0x000004
SAMPLE_DURATION_PRESENT: int = 0x000100
SAMPLE_SIZE_PRESENT: int = 0x000200
SAMPLE_FLAGS_PRESENT: int = 0x000400
SAMPLE_COMPOSITION_PRESENT: int = 0x000800
DECODE_TIME_LAYOUTS: dict[int, str] = {0: ">I", 1: ">Q"}


@dataclass(frozen=True)
class SampleDefaults:
    """A sample's duration and size where a fragment does not give them."""

    duration: int = 0
    size: int = 0


def read_track_defaults(content: bytes, movie: Mp4Box) -> dict[int, SampleDefaults]:
    """Each track's defaults in the movie extends box ('mvex' > 'trex')."""

    extends: Mp4Box | None = only_child(content, movie, b"mvex")
    defaults: dict[int, SampleDefaults] = {}
    for track in [] if extends is None else child_boxes(content, extends, b"trex"):
        _, _, at = full_box_fields(content, track)
        track_id, _, duration, size, _ = read_fields(content, track, ">IIIII", at)
        defaults[track_id] = SampleDefaults(duration=duration, size=size)
    return defaults


def read_fragment(
    content: bytes,
    fragment: Mp4Box,
    tracks: dict[int, SoundTrack],
    defaults: dict[int, SampleDefaults],
) -> None:
    """
    Every sample of one movie fragment ('moof'), counted into its track,
    and each track fragment's end time as a claim.

    Raises:
        Mp4StructureError: a fragment of a track the movie lacks, or runs
            that do not add up.
    """

    data_end: int = fragment.start
    for index, track_fragment in enumerate(child_boxes(content, fragment, b"traf")):
        header: Mp4Box = required_child(content, track_fragment, b"tfhd")
        _, flags, at = full_box_fields(content, header)
        (track_id,) = read_fields(content, header, ">I", at)
        at += 4
        track: SoundTrack | None = tracks.get(track_id)
        if track is None:
            raise Mp4StructureError("A fragment of a track the movie lacks.")

        if flags & BASE_DATA_OFFSET_PRESENT:
            (base,) = read_fields(content, header, ">Q", at)
            at += 8
        elif flags & DEFAULT_BASE_IS_MOOF or index == 0:
            base = fragment.start
        else:
            base = data_end
        if flags & DESCRIPTION_INDEX_PRESENT:
            at += 4

        sample = defaults.get(track_id, SampleDefaults())
        if flags & DEFAULT_DURATION_PRESENT:
            sample = SampleDefaults(
                read_fields(content, header, ">I", at)[0], sample.size
            )
            at += 4
        if flags & DEFAULT_SIZE_PRESENT:
            sample = SampleDefaults(
                sample.duration, read_fields(content, header, ">I", at)[0]
            )

        position: int = base
        elapsed: int = 0
        for run in child_boxes(content, track_fragment, b"trun"):
            position, elapsed = read_run(
                content, run, track, base, position, elapsed, sample
            )
        track.claim(decode_time(content, track_fragment) + elapsed, track.timescale)
        data_end = position


def read_run(
    content: bytes,
    run: Mp4Box,
    track: SoundTrack,
    base: int,
    position: int,
    elapsed: int,
    defaults: SampleDefaults,
) -> tuple[int, int]:
    """
    One track run's samples, from its data offset (else right after the run
    before); where its data ends and the time it adds.
    """

    _, flags, at = full_box_fields(content, run)
    (count,) = read_fields(content, run, ">I", at)
    at += 4
    if flags & DATA_OFFSET_PRESENT:
        (offset,) = read_fields(content, run, ">i", at)
        position = base + offset
        at += 4
    if flags & FIRST_SAMPLE_FLAGS_PRESENT:
        at += 4

    has_duration: bool = bool(flags & SAMPLE_DURATION_PRESENT)
    has_size: bool = bool(flags & SAMPLE_SIZE_PRESENT)
    entry_bytes: int = 4 * sum(
        bool(flags & present)
        for present in (
            SAMPLE_DURATION_PRESENT,
            SAMPLE_SIZE_PRESENT,
            SAMPLE_FLAGS_PRESENT,
            SAMPLE_COMPOSITION_PRESENT,
        )
    )
    for index in range(count):
        entry_at: int = at + index * entry_bytes
        duration: int = (
            read_fields(content, run, ">I", entry_at)[0]
            if has_duration
            else defaults.duration
        )
        size: int = (
            read_fields(content, run, ">I", entry_at + 4 * has_duration)[0]
            if has_size
            else defaults.size
        )
        track.add_sample(content, position, size)
        position += size
        elapsed += duration
    return position, elapsed


def decode_time(content: bytes, track_fragment: Mp4Box) -> int:
    """When the track fragment begins ('tfdt'), in the track's time scale."""

    found: Mp4Box | None = only_child(content, track_fragment, b"tfdt")
    if found is None:
        return 0

    version, _, at = full_box_fields(content, found)
    if version not in DECODE_TIME_LAYOUTS:
        raise Mp4StructureError("An unknown decode time version.")

    (time,) = read_fields(content, found, DECODE_TIME_LAYOUTS[version], at)
    return time
