"""How fast a client's customers hear back (admin client health)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.client_health.constrained_integers import (
    MeasuredReplyCount,
    ReplyLatencyPercentileMilliseconds,
)
from app.schemas.typings.storage.constrained_integers import DocumentBucketIndex


class ReplyLatencyBucketCount(ImmutableDTO):
    """Assistant replies of one channel whose wait fell into one bucket."""

    channel: ChannelKind
    bucket: DocumentBucketIndex
    count: MeasuredReplyCount


class ChannelReplySpeed(ImmutableDTO):
    """
    The replies of one channel: how many were measured, and the median and
    95th percentile of the customer's wait (first unanswered message to the
    stored answer).
    """

    channel: ChannelKind
    reply_count: MeasuredReplyCount
    p50_ms: ReplyLatencyPercentileMilliseconds
    p95_ms: ReplyLatencyPercentileMilliseconds


class ClientReplySpeed(ImmutableDTO):
    """
    Reply speed of a client in the last 7 days, over every channel and per
    channel (the busiest first). Percentiles are None without measured
    replies; replies before measuring began (or of the owner's test chat
    and voice calls) are not measured.
    """

    reply_count: MeasuredReplyCount = MeasuredReplyCount(0)
    p50_ms: ReplyLatencyPercentileMilliseconds | None = None
    p95_ms: ReplyLatencyPercentileMilliseconds | None = None
    channels: list[ChannelReplySpeed] = Field(default_factory=list[ChannelReplySpeed])
