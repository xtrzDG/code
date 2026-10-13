"""
A sound track of an MP4 recording: its codec, what its samples hold and
what its tables claim.

Each sample of a track is one AAC frame (1024 samples of the core rate)
or one Opus packet (its TOC byte says how long it plays). Their sum is the
length a decoder plays; the track's durations (media header, time-to-
sample table, fragment runs) are claims kept beside it.
"""

from dataclasses import dataclass, field

from app.utilities.media.aac_config import AAC_FRAME_SAMPLES, read_aac_core_rate
from app.utilities.media.mp4_boxes import (
    Mp4Box,
    Mp4StructureError,
    full_box_fields,
    iterate_boxes,
    only_child,
    read_fields,
    required_child,
)
from app.utilities.media.opus_packets import OPUS_SAMPLE_RATE, opus_packet_samples

AAC_SAMPLE_ENTRY: bytes = b"mp4a"
OPUS_SAMPLE_ENTRY: bytes = b"Opus"
# SampleEntry (6 reserved, data reference index) and AudioSampleEntry fields.
AUDIO_SAMPLE_ENTRY_BYTES: int = 28
SOUND_DESCRIPTION_VERSION_AT: int = 8
# QuickTime sound descriptions 1 and 2 add fields before the child boxes.
SOUND_DESCRIPTION_EXTRA_BYTES: dict[int, int] = {0: 0, 1: 16, 2: 36}
PACKET_HEAD_BYTES: int = 2
# An hour of 20 ms Opus packets is 180,000 samples; far more is not a voice note.
MOST_SAMPLES: int = 500_000


@dataclass(frozen=True)
class Mp4AudioCodec:
    """
    How long a track's samples play: AAC frames of `frame_samples` at
    `sample_rate`, or Opus packets (no `frame_samples`), each read.
    """

    sample_rate: int
    frame_samples: int | None


@dataclass
class SoundTrack:
    """One sound track: its clock, codec, samples counted and claims made."""

    track_id: int
    timescale: int
    codec: Mp4AudioCodec
    sample_count: int = 0
    codec_samples: int = 0
    claimed_seconds: list[float] = field(default_factory=list[float])

    def claim(self, ticks: int, timescale: int) -> None:
        """A duration the file states, in units of `timescale` a second."""

        if timescale <= 0:
            raise Mp4StructureError("A timescale is zero.")
        self.claimed_seconds.append(ticks / timescale)

    def add_sample(self, content: bytes, position: int, size: int) -> None:
        """One sample of `size` bytes at `position` of the file."""

        self.sample_count += 1
        if self.sample_count > MOST_SAMPLES:
            raise Mp4StructureError("Too many samples for a voice note.")

        if self.codec.frame_samples is not None:
            self.codec_samples += self.codec.frame_samples
            return

        if size <= 0 or position < 0 or position + size > len(content):
            raise Mp4StructureError("A sample lies outside the file.")

        samples: int | None = opus_packet_samples(
            content[position : position + min(size, PACKET_HEAD_BYTES)]
        )
        if samples is None:
            raise Mp4StructureError("A sample is not an Opus packet.")
        self.codec_samples += samples

    def longest_seconds(self) -> float:
        """The larger of the samples' own length and every claim."""

        played: float = self.codec_samples / self.codec.sample_rate
        return max([played, *self.claimed_seconds])


def read_audio_codec(content: bytes, sample_table: Mp4Box) -> Mp4AudioCodec:
    """The codec of the track's one sample description: AAC or Opus."""

    descriptions: Mp4Box = required_child(content, sample_table, b"stsd")
    _, _, at = full_box_fields(content, descriptions)
    (entry_count,) = read_fields(content, descriptions, ">I", at)
    entries: list[Mp4Box] = list(iterate_boxes(content, at + 4, descriptions.end))
    if entry_count != 1 or len(entries) != 1:
        raise Mp4StructureError("A track has more than one sample description.")

    entry: Mp4Box = entries[0]
    if entry.kind == OPUS_SAMPLE_ENTRY:
        return Mp4AudioCodec(sample_rate=OPUS_SAMPLE_RATE, frame_samples=None)

    if entry.kind != AAC_SAMPLE_ENTRY:
        raise Mp4StructureError("The track's audio is neither AAC nor Opus.")

    (version,) = read_fields(
        content, entry, ">H", entry.data_start + SOUND_DESCRIPTION_VERSION_AT
    )
    if version not in SOUND_DESCRIPTION_EXTRA_BYTES:
        raise Mp4StructureError("An unknown sound description version.")

    children_at: int = (
        entry.data_start
        + AUDIO_SAMPLE_ENTRY_BYTES
        + SOUND_DESCRIPTION_EXTRA_BYTES[version]
    )
    children = Mp4Box(
        kind=entry.kind, start=entry.start, data_start=children_at, end=entry.end
    )
    config: Mp4Box | None = only_child(content, children, b"esds")
    wave: Mp4Box | None = only_child(content, children, b"wave")
    if config is None and wave is not None:
        config = only_child(content, wave, b"esds")
    if config is None:
        raise Mp4StructureError("The AAC track has no decoder config.")

    _, _, descriptors_at = full_box_fields(content, config)
    rate: int = read_aac_core_rate(content[descriptors_at : config.end])
    return Mp4AudioCodec(sample_rate=rate, frame_samples=AAC_FRAME_SAMPLES)
