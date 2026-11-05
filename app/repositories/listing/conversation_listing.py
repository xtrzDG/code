"""Pages and counts of conversations: the feed and the dashboard."""

from typed_time_provider import Microseconds

from app.repositories.aggregate_reading import (
    parse_choice,
    period_range,
    segment_of,
    timeline_buckets,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    LAST_MESSAGE_AT_FIELD,
    STATUS_FIELD,
)
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    IS_SANDBOX_FIELD,
    field_equals,
    time_range,
    without_sandbox,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.listing_filters import ConversationFeedFilter
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    ConversationMixCount,
    ConversationTimelineCount,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_queries import (
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CHANNEL_FIELD: DocumentFieldPath = DocumentFieldPath("channel")
LANGUAGE_FIELD: DocumentFieldPath = DocumentFieldPath("language")
IS_AFTER_HOURS_FIELD: DocumentFieldPath = DocumentFieldPath("is_after_hours")
TRUE_TEXT: str = "true"


class ConversationListing(BusinessScopedRepository[ConversationDocument]):
    """The feed newest first, and what started in a period."""

    def page_feed(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        feed: ConversationFeedFilter,
    ) -> list[ConversationDocument]:
        matches: list[DocumentFieldMatch] = []
        if feed.channel is not None:
            matches.append(field_equals(CHANNEL_FIELD, feed.channel))

        if feed.status is not None:
            matches.append(field_equals(STATUS_FIELD, feed.status))

        ranges: list[DocumentFieldRange] = []
        if feed.last_message_from is not None:
            ranges.append(
                time_range(LAST_MESSAGE_AT_FIELD, starting_at=feed.last_message_from)
            )

        if feed.started_before is not None:
            ranges.append(
                time_range(CREATED_AT_FIELD, ending_before=feed.started_before)
            )

        return self._page_in_business(
            business_id,
            (LAST_MESSAGE_AT_FIELD,),
            window,
            DocumentFilter(
                matches=tuple(matches),
                excluding=() if feed.include_sandbox else (without_sandbox(),),
                ranges=tuple(ranges),
            ),
        )

    def count_started_by_mix(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> list[ConversationMixCount]:
        groups = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    excluding=(without_sandbox(),),
                    ranges=(time_range(CREATED_AT_FIELD, start, end),),
                ),
                group_by=(CHANNEL_FIELD, LANGUAGE_FIELD),
            ),
        )
        return [
            ConversationMixCount(
                channel=channel,
                language=None if language is None else LanguageTag(str(language)),
                count=PeriodItemCount(int(group.count)),
            )
            for group in groups
            if (channel := parse_choice(ChannelKind, group.values[0])) is not None
            for language in (group.values[1],)
        ]

    def count_started_by_timeline(
        self,
        business_id: BusinessId,
        period: ActivityPeriod,
    ) -> list[ConversationTimelineCount]:
        groups = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    excluding=(without_sandbox(),),
                    ranges=(period_range(CREATED_AT_FIELD, period),),
                ),
                group_by=(IS_AFTER_HOURS_FIELD,),
                buckets=timeline_buckets(CREATED_AT_FIELD, period),
            ),
        )
        return [
            ConversationTimelineCount(
                is_after_hours=group.values[0] is not None
                and str(group.values[0]) == TRUE_TEXT,
                segment=segment_of(group),
                count=PeriodItemCount(int(group.count)),
            )
            for group in groups
        ]

    def list_sandbox_active_since(
        self,
        business_id: BusinessId,
        since: Microseconds,
    ) -> list[ConversationId]:
        """Sandbox conversations with a message from `since` on."""

        return [
            conversation.id
            for conversation in self._list_in_range(
                business_id,
                time_range(LAST_MESSAGE_AT_FIELD, starting_at=since),
                [field_equals(IS_SANDBOX_FIELD, True)],
            )
        ]
