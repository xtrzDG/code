"""Pages and counts of handoffs and unanswered questions."""

from typed_time_provider import Microseconds

from app.repositories.aggregate_reading import (
    parse_choice,
    period_count,
    period_range,
    segment_of,
    timeline_buckets,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_among,
    field_equals,
    time_range,
    without_sandbox,
)
from app.repositories.listing.booking_listing import (
    CONVERSATION_ID_FIELD,
    STATUS_FIELD,
    sandbox_exclusion,
)
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.dto.listing_filters import HandoffListFilter
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    HandoffActivityCount,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.booleans import IsResolvedIncluded
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

URGENCY_FIELD: DocumentFieldPath = DocumentFieldPath("urgency")
REASON_FIELD: DocumentFieldPath = DocumentFieldPath("reason")
RESOLVED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("resolved_at")
IS_RESOLVED_FIELD: DocumentFieldPath = DocumentFieldPath("is_resolved")
OCCURRENCE_COUNT_FIELD: DocumentFieldPath = DocumentFieldPath("occurrence_count")
LAST_SEEN_AT_FIELD: DocumentFieldPath = DocumentFieldPath("last_seen_at")
# A handoff waits for a person in every status but resolved.
OPEN_STATUSES: tuple[HandoffStatus, ...] = tuple(
    status for status in HandoffStatus if status is not HandoffStatus.RESOLVED
)


class HandoffListing(BusinessScopedRepository[HandoffDocument]):
    """
    The work queue of a business's handoffs: open ones of one urgency the
    oldest first, resolved ones the most recently resolved first (the
    resolution always stamps `resolved_at`), and their counts.
    """

    def page_open(
        self,
        business_id: BusinessId,
        urgency: HandoffUrgency,
        window: KeysetSlice,
        listing: HandoffListFilter,
    ) -> list[HandoffDocument]:
        statuses: tuple[HandoffStatus, ...] = (
            OPEN_STATUSES if listing.status is None else (listing.status,)
        )
        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            DocumentFilter(
                matches=(field_equals(URGENCY_FIELD, urgency),),
                among=(field_among(STATUS_FIELD, statuses),),
                excluding=sandbox_exclusion(listing.include_sandbox),
            ),
            is_descending=False,
        )

    def page_resolved(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        include_sandbox: IsSandboxIncluded,
    ) -> list[HandoffDocument]:
        return self._page_in_business(
            business_id,
            (RESOLVED_AT_FIELD,),
            window,
            DocumentFilter(
                matches=(field_equals(STATUS_FIELD, HandoffStatus.RESOLVED),),
                excluding=sandbox_exclusion(include_sandbox),
            ),
        )

    def count_by_status(
        self,
        business_id: BusinessId,
        include_sandbox: IsSandboxIncluded,
    ) -> dict[HandoffStatus, ListItemCount]:
        counts: dict[HandoffStatus, ListItemCount] = {}
        for group in self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(excluding=sandbox_exclusion(include_sandbox)),
                group_by=(STATUS_FIELD,),
            ),
        ):
            status: HandoffStatus | None = parse_choice(HandoffStatus, group.values[0])
            if status is not None:
                counts[status] = ListItemCount(int(group.count))

        return counts

    def count_made(
        self,
        business_id: BusinessId,
        period: ActivityPeriod,
    ) -> list[HandoffActivityCount]:
        groups = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    excluding=(without_sandbox(),),
                    ranges=(period_range(CREATED_AT_FIELD, period),),
                ),
                group_by=(REASON_FIELD, URGENCY_FIELD),
                buckets=timeline_buckets(CREATED_AT_FIELD, period),
            ),
        )
        return [
            HandoffActivityCount(
                reason=reason,
                urgency=urgency,
                segment=segment_of(group),
                count=PeriodItemCount(int(group.count)),
            )
            for group in groups
            if (reason := parse_choice(HandoffReason, group.values[0])) is not None
            and (urgency := parse_choice(HandoffUrgency, group.values[1])) is not None
        ]

    def count_made_since(
        self,
        business_id: BusinessId,
        since: Microseconds,
    ) -> PeriodItemCount:
        return period_count(
            self._aggregate_in_business(
                business_id,
                DocumentAggregation(
                    where=DocumentFilter(
                        excluding=(without_sandbox(),),
                        ranges=(time_range(CREATED_AT_FIELD, starting_at=since),),
                    )
                ),
            )
        )

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[HandoffDocument]:
        return sorted(
            self._list_in_business(
                business_id, [field_equals(CONVERSATION_ID_FIELD, conversation_id)]
            ),
            key=lambda handoff: int(handoff.created_at),
            reverse=True,
        )


class UnansweredQuestionListing(BusinessScopedRepository[UnansweredQuestionDocument]):
    """Unanswered questions most asked first, and how many are open."""

    def page_by_rank(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        include_resolved: IsResolvedIncluded,
        include_sandbox: IsSandboxIncluded,
    ) -> list[UnansweredQuestionDocument]:
        return self._page_in_business(
            business_id,
            (OCCURRENCE_COUNT_FIELD, LAST_SEEN_AT_FIELD),
            window,
            DocumentFilter(
                matches=()
                if include_resolved
                else (field_equals(IS_RESOLVED_FIELD, False),),
                excluding=sandbox_exclusion(include_sandbox),
            ),
        )

    def count_open(self, business_id: BusinessId) -> ListItemCount:
        return ListItemCount(
            int(
                period_count(
                    self._aggregate_in_business(
                        business_id,
                        DocumentAggregation(
                            where=DocumentFilter(
                                matches=(field_equals(IS_RESOLVED_FIELD, False),),
                                excluding=(without_sandbox(),),
                            )
                        ),
                    )
                )
            )
        )
