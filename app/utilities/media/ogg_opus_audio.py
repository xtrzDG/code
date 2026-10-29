"""
How long an Ogg Opus recording is, from its pages and its packets.

A page's granule position is a claim its writer made; each audio packet
says how long it plays (`opus_packets`). The length is the larger of the
two, so neither a forged last page nor forged granules make a recording
shorter than a decoder plays it. Only an Opus stream counts: its first
packet is the identification header, its second the comment header.
"""

import math
from dataclasses import dataclass, field

from app.utilities.media.ogg_pages import (
    CONTINUED_PACKET,
    OggPage,
    OggStructureError,
    read_ogg_pages,
)
from app.utilities.media.opus_packets import OPUS_SAMPLE_RATE, opus_packet_samples

OPUS_HEAD: bytes = b"OpusHead"
OPUS_TAGS: bytes = b"OpusTags"
PACKET_PREFIX_BYTES: int = len(OPUS_HEAD)
FULL_SEGMENT: int = 255
NO_PACKET_ENDS: int = -1
HEADER_PACKETS: int = 2
# An hour of 20 ms packets is 180,000; a file of far more is not a voice note.
MOST_PACKETS: int = 500_000


@dataclass
class OpusTally:
    """The packets read so far and what they and the pages say."""

    packets: int = 0
    samples: int = 0
    latest_granule: int = 0
    prefix: bytearray = field(default_factory=bytearray)
    is_open: bool = False

    def end_packet(self) -> None:
        """The packet whose first bytes `prefix` holds ended."""

        start: bytes = bytes(self.prefix)
        self.prefix.clear()
        if self.packets == 0 and not start.startswith(OPUS_HEAD):
            raise OggStructureError("The stream is not Opus.")

        if self.packets == 1 and not start.startswith(OPUS_TAGS):
            raise OggStructureError("The Opus comment header is missing.")

        if self.packets >= HEADER_PACKETS:
            samples: int | None = opus_packet_samples(start)
            if samples is None:
                raise OggStructureError("A packet is not an Opus packet.")
            self.samples += samples

        self.packets += 1
        if self.packets > MOST_PACKETS:
            raise OggStructureError("Too many packets for a voice note.")


def read_ogg_opus_seconds(content: bytes) -> int | None:
    """
    Whole seconds (rounded up) of an Ogg Opus recording; None for any other
    file, a stream that is not Opus, or one whose structure does not hold.
    """

    try:
        samples: int = count_ogg_opus_samples(content)
    except OggStructureError:
        return None

    return math.ceil(samples / OPUS_SAMPLE_RATE)


def count_ogg_opus_samples(content: bytes) -> int:
    """
    The larger of the latest granule position and the packets' own length,
    in 48 kHz samples.

    Raises:
        OggStructureError: not one well-formed Ogg Opus stream.
    """

    tally = OpusTally()
    for page in read_ogg_pages(content):
        if bool(page.flags & CONTINUED_PACKET) != tally.is_open:
            raise OggStructureError("A page does not continue the packet before.")

        if page.granule < NO_PACKET_ENDS:
            raise OggStructureError("A granule position is negative.")

        read_packets(page, tally)
        tally.latest_granule = max(tally.latest_granule, page.granule)

    if tally.packets < HEADER_PACKETS:
        raise OggStructureError("The Opus headers are missing.")

    return max(tally.samples, tally.latest_granule)


def read_packets(page: OggPage, tally: OpusTally) -> None:
    """Each segment of the page; one shorter than 255 bytes ends a packet."""

    offset: int = 0
    for length in page.lacing:
        missing: int = PACKET_PREFIX_BYTES - len(tally.prefix)
        if missing > 0:
            tally.prefix += page.body[offset : offset + min(length, missing)]
        offset += length
        tally.is_open = length == FULL_SEGMENT
        if not tally.is_open:
            tally.end_packet()
