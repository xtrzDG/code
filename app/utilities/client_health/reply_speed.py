"""
How fast a client's customers hear back: the database counts the assistant
replies of the last 7 days per channel and latency bucket; the median and
the 95th percentile are read from the buckets.
"""

from collections import defaultdict
from collections.abc import Sequence

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.reply_speed import (
    ChannelReplySpeed,
    ClientReplySpeed,
    ReplyLatencyBucketCount,
)
from app.schemas.typings.client_health.constrained_integers import (
    MeasuredReplyCount,
    ReplyLatencyPercentileMilliseconds,
)

# Bucket starts in milliseconds; the SLOW_REPLIES threshold (15 s) is one
# of them, so whether a client is slow never depends on where inside a
# bucket a wait lies.
REPLY_LATENCY_BUCKET_STARTS: tuple[int, ...] = (
    0, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000,
    15000, 20000, 25000, 30000, 45000, 60000, 90000, 120000, 180000, 300000,
)  # fmt: skip
MEDIAN: float = 0.5
P95: float = 0.95
# SLOW_REPLIES: the 95th percentile above 15 s, over at least this many
# measured replies (one slow answer of a quiet client is not a pattern).
SLOW_REPLY_P95_MS: int = 15_000
MIN_MEASURED_REPLIES: int = 10


def percentile_of(counts: dict[int, int], fraction: float) -> int:
    """
    The wait below which `fraction` of the replies lie, interpolated inside
    its bucket; a wait in the open last bucket reads as that bucket's start.
    """

    starts: tuple[int, ...] = REPLY_LATENCY_BUCKET_STARTS
    total: int = sum(counts.values())
    target: float = fraction * total
    seen: int = 0
    for index in sorted(counts):
        count: int = counts[index]
        if count > 0 and seen + count >= target:
            lower: int = starts[index]
            if index + 1 >= len(starts):
                return lower
            upper: int = starts[index + 1]
            return round(lower + (target - seen) / count * (upper - lower))
        seen += count

    return starts[-1]


def build_client_reply_speed(
    buckets: Sequence[ReplyLatencyBucketCount],
) -> ClientReplySpeed:
    """Every channel together and each channel, the busiest first."""

    by_channel: dict[ChannelKind, dict[int, int]] = defaultdict(dict)
    overall: dict[int, int] = {}
    for bucket in buckets:
        index: int = int(bucket.bucket)
        if index >= len(REPLY_LATENCY_BUCKET_STARTS):
            continue
        cell = by_channel[bucket.channel]
        cell[index] = cell.get(index, 0) + int(bucket.count)
        overall[index] = overall.get(index, 0) + int(bucket.count)

    total: int = sum(overall.values())
    if total == 0:
        return ClientReplySpeed()

    channels: list[ChannelReplySpeed] = [
        ChannelReplySpeed(
            channel=channel,
            reply_count=MeasuredReplyCount(sum(counts.values())),
            p50_ms=ReplyLatencyPercentileMilliseconds(percentile_of(counts, MEDIAN)),
            p95_ms=ReplyLatencyPercentileMilliseconds(percentile_of(counts, P95)),
        )
        for channel, counts in by_channel.items()
        if sum(counts.values()) > 0
    ]
    return ClientReplySpeed(
        reply_count=MeasuredReplyCount(total),
        p50_ms=ReplyLatencyPercentileMilliseconds(percentile_of(overall, MEDIAN)),
        p95_ms=ReplyLatencyPercentileMilliseconds(percentile_of(overall, P95)),
        channels=sorted(
            channels, key=lambda speed: (-int(speed.reply_count), speed.channel.value)
        ),
    )


def is_slow(speed: ClientReplySpeed) -> bool:
    """SLOW_REPLIES: enough replies, and more than one in twenty took 15 s."""

    return (
        int(speed.reply_count) >= MIN_MEASURED_REPLIES
        and speed.p95_ms is not None
        and int(speed.p95_ms) > SLOW_REPLY_P95_MS
    )
