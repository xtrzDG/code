"""How long customers waited for the assistant's replies, counted in buckets."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import AUTHOR_FIELD, CREATED_AT_FIELD
from app.repositories.document_queries import field_equals, time_range
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.reply_speed import ReplyLatencyBucketCount
from app.schemas.dto.storage_aggregates import (
    DocumentAggregation,
    DocumentFieldBuckets,
    DocumentGroupCount,
)
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_integers import (
    MeasuredReplyCount,
)
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.storage.constrained_integers import DocumentBucketIndex
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

CHANNEL_FIELD: DocumentFieldPath = DocumentFieldPath("channel")
REPLY_LATENCY_FIELD: DocumentFieldPath = DocumentFieldPath("reply_latency_ms")


class ReplyLatencyReading(BusinessScopedRepository[MessageDocument]):
    """
    The assistant replies of a period per channel and latency bucket, in
    one indexed aggregation (`messages_doc_reply_latency_idx`, 1090).
    """

    def count_reply_latencies(
        self,
        business_id: BusinessId,
        since: Microseconds,
        bucket_starts: Sequence[ReplyLatencyMilliseconds],
    ) -> list[ReplyLatencyBucketCount]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(AUTHOR_FIELD, MessageAuthor.ASSISTANT),),
                    ranges=(time_range(CREATED_AT_FIELD, starting_at=since),),
                ),
                group_by=(CHANNEL_FIELD,),
                buckets=DocumentFieldBuckets(
                    field=REPLY_LATENCY_FIELD,
                    starts=tuple(
                        DocumentFieldInteger(int(start)) for start in bucket_starts
                    ),
                ),
            ),
        )
        return [
            count for group in groups if (count := read_bucket_count(group)) is not None
        ]


def read_bucket_count(group: DocumentGroupCount) -> ReplyLatencyBucketCount | None:
    """
    One group as a typed count; None for a reply without a channel or one
    this release cannot read (written by a newer release during a deploy).
    """

    (channel_text,) = group.values
    channel: ChannelKind | None = parse_choice(ChannelKind, channel_text)
    if channel is None or group.bucket is None:
        return None

    return ReplyLatencyBucketCount(
        channel=channel,
        bucket=DocumentBucketIndex(int(group.bucket)),
        count=MeasuredReplyCount(int(group.count)),
    )
