"""
A track of an MP4 recording read from its 'trak' box: its id, clock and
codec, the durations its headers, edit list and time-to-sample table
claim, and every sample its sample tables place in the file (chunk
offsets, samples per chunk, sample sizes), as a decoder finds them.
"""

from collections.abc import Iterator

from app.utilities.media.mp4_boxes import (
    Mp4Box,
    Mp4StructureError,
    full_box_fields,
    only_child,
    read_fields,
    read_versioned_fields,
    required_child,
)
from app.utilities.media.mp4_sound_track import (
    MOST_SAMPLES,
    SoundTrack,
    read_audio_codec,
)

SOUND_HANDLER: bytes = b"soun"
HANDLER_TYPE_AT: int = 4
# Version 1 headers hold 64-bit times and durations, version 0 32-bit ones.
TRACK_HEADER_LAYOUTS: dict[int, str] = {0: ">8xI4xI", 1: ">16xI4xQ"}
MEDIA_HEADER_LAYOUTS: dict[int, str] = {0: ">8xII", 1: ">16xIQ"}
EDIT_LAYOUTS: dict[int, str] = {0: ">Ii4x", 1: ">Qq4x"}


def read_sound_track(content: bytes, track: Mp4Box, movie_timescale: int) -> SoundTrack:
    """
    A sound track and its samples in the sample tables (none in a
    fragmented file: its samples come in the fragments).

    Raises:
        Mp4StructureError: not a sound track of AAC or Opus, or tables that
            do not add up.
    """

    media: Mp4Box = required_child(content, track, b"mdia")
    track_id, track_duration = read_versioned_fields(
        content, required_child(content, track, b"tkhd"), TRACK_HEADER_LAYOUTS
    )
    timescale, media_duration = read_versioned_fields(
        content, required_child(content, media, b"mdhd"), MEDIA_HEADER_LAYOUTS
    )
    handler: Mp4Box = required_child(content, media, b"hdlr")
    _, _, handler_at = full_box_fields(content, handler)
    type_at: int = handler_at + HANDLER_TYPE_AT
    if content[type_at : min(type_at + 4, handler.end)] != SOUND_HANDLER:
        raise Mp4StructureError("A track that is not sound.")

    sample_table: Mp4Box = required_child(
        content, required_child(content, media, b"minf"), b"stbl"
    )
    sound = SoundTrack(
        track_id=track_id,
        timescale=timescale,
        codec=read_audio_codec(content, sample_table),
    )
    sound.claim(media_duration, timescale)
    sound.claim(track_duration, movie_timescale)
    sound.claim(edited_duration(content, track), movie_timescale)
    sound.claim(table_duration(content, sample_table), timescale)
    for position, size in table_samples(content, sample_table):
        sound.add_sample(content, position, size)
    return sound


def edited_duration(content: bytes, track: Mp4Box) -> int:
    """
    The edit list's total, in movie time: its edits (an empty one plays
    silence, two may repeat the same media) are what a player plays.
    """

    edits: Mp4Box | None = only_child(content, track, b"edts")
    edit_list: Mp4Box | None = (
        None if edits is None else only_child(content, edits, b"elst")
    )
    if edit_list is None:
        return 0

    version, _, at = full_box_fields(content, edit_list)
    if version not in EDIT_LAYOUTS:
        raise Mp4StructureError("An unknown edit list version.")

    layout: str = EDIT_LAYOUTS[version]
    (count,) = read_fields(content, edit_list, ">I", at)
    entry_bytes: int = 12 if version == 0 else 20
    return sum(
        read_fields(content, edit_list, layout, at + 4 + index * entry_bytes)[0]
        for index in range(count)
    )


def table_duration(content: bytes, sample_table: Mp4Box) -> int:
    """The time-to-sample table's total: each run's count times its delta."""

    timing: Mp4Box | None = only_child(content, sample_table, b"stts")
    if timing is None:
        return 0

    _, _, at = full_box_fields(content, timing)
    (count,) = read_fields(content, timing, ">I", at)
    total: int = 0
    for index in range(count):
        samples, delta = read_fields(content, timing, ">II", at + 4 + index * 8)
        total += samples * delta
    return total


def table_samples(content: bytes, sample_table: Mp4Box) -> Iterator[tuple[int, int]]:
    """Where each sample of the tables is (file offset) and its size."""

    sizes: Mp4Box | None = only_child(content, sample_table, b"stsz")
    if only_child(content, sample_table, b"stz2") is not None:
        raise Mp4StructureError("Compact sample sizes are not a browser's.")
    if sizes is None:
        return

    _, _, sizes_at = full_box_fields(content, sizes)
    constant_size, count = read_fields(content, sizes, ">II", sizes_at)
    if count == 0:
        return
    if count > MOST_SAMPLES:
        raise Mp4StructureError("Too many samples for a voice note.")

    runs: list[tuple[int, int]] = chunk_runs(content, sample_table)
    run: int = -1
    sample: int = 0
    for chunk, offset in enumerate(chunk_offsets(content, sample_table), start=1):
        # The last run that began by this chunk says how many samples it holds.
        while run + 1 < len(runs) and runs[run + 1][0] <= chunk:
            run += 1
        position: int = offset
        for _ in range(runs[run][1] if run >= 0 else 0):
            if sample >= count:
                return
            size: int = (
                constant_size
                or read_fields(content, sizes, ">I", sizes_at + 8 + 4 * sample)[0]
            )
            yield position, size
            position += size
            sample += 1


def chunk_offsets(content: bytes, sample_table: Mp4Box) -> list[int]:
    """Each chunk's file offset ('stco' or 'co64', exactly one of them)."""

    short: Mp4Box | None = only_child(content, sample_table, b"stco")
    large: Mp4Box | None = only_child(content, sample_table, b"co64")
    if short is not None and large is None:
        table, field_layout, width = short, ">I", 4
    elif large is not None and short is None:
        table, field_layout, width = large, ">Q", 8
    else:
        raise Mp4StructureError("The chunk offsets are missing or doubled.")

    _, _, at = full_box_fields(content, table)
    (count,) = read_fields(content, table, ">I", at)
    if count > MOST_SAMPLES:
        raise Mp4StructureError("Too many chunks for a voice note.")

    return [
        read_fields(content, table, field_layout, at + 4 + index * width)[0]
        for index in range(count)
    ]


def chunk_runs(content: bytes, sample_table: Mp4Box) -> list[tuple[int, int]]:
    """The sample-to-chunk runs: (first chunk, samples per chunk), ascending."""

    table: Mp4Box = required_child(content, sample_table, b"stsc")
    _, _, at = full_box_fields(content, table)
    (count,) = read_fields(content, table, ">I", at)
    runs: list[tuple[int, int]] = []
    for index in range(count):
        first, per_chunk, _ = read_fields(content, table, ">III", at + 4 + index * 12)
        if first < 1 or (runs and first <= runs[-1][0]):
            raise Mp4StructureError("The sample-to-chunk runs are out of order.")
        runs.append((first, per_chunk))
    return runs
