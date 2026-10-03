"""Pages and counts of bookings and leads (the cabinet's lists, the dashboard)."""

from collections.abc import Sequence

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
    field_equals,
    time_range,
    without_sandbox,
)
from app.schemas.constants.bookings import BookingOrder, BookingStatus, LeadStatus
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.dto.listing_filters import BookingListFilter
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    BookingActivityCount,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation
from app.schemas.dto.storage_queries import (
    DocumentFieldExclusion,
    DocumentFieldMatch,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")
ENDS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("ends_at")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
RESOURCE_ID_FIELD: DocumentFieldPath = DocumentFieldPath("resource_id")
CONVERSATION_ID_FIELD: DocumentFieldPath = DocumentFieldPath("conversation_id")


def sandbox_exclusion(
    include_sandbox: IsSandboxIncluded,
) -> tuple[DocumentFieldExclusion, ...]:
    return () if include_sandbox else (without_sandbox(),)


class BookingListing(BusinessScopedRepository[BookingDocument]):
    """Keyset pages and counts of a business's bookings."""

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        listing: BookingListFilter,
    ) -> list[BookingDocument]:
        matches: list[DocumentFieldMatch] = []
        if listing.status is not None:
            matches.append(field_equals(STATUS_FIELD, listing.status))

        if listing.resource_id is not None:
            matches.append(field_equals(RESOURCE_ID_FIELD, listing.resource_id))

        ranges: tuple[DocumentFieldRange, ...] = ()
        if listing.starts_from is not None or listing.starts_before is not None:
            ranges = (
                DocumentFieldRange(
                    field=STARTS_AT_FIELD,
                    lower=(
                        None
                        if listing.starts_from is None
                        else DocumentFieldInteger(int(listing.starts_from))
                    ),
                    upper=(
                        None
                        if listing.starts_before is None
                        else DocumentFieldInteger(int(listing.starts_before))
                    ),
                ),
            )

        return self._page_in_business(
            business_id,
            (STARTS_AT_FIELD,),
            window,
            DocumentFilter(
                matches=tuple(matches),
                excluding=sandbox_exclusion(listing.include_sandbox),
                ranges=ranges,
            ),
            is_descending=listing.order is BookingOrder.LATEST_FIRST,
        )

    def list_ending_after(
        self,
        business_id: BusinessId,
        moment: BookingSearchBoundSeconds,
    ) -> list[BookingDocument]:
        bookings: list[BookingDocument] = self._list_in_range(
            business_id,
            DocumentFieldRange(
                field=ENDS_AT_FIELD, lower=DocumentFieldInteger(int(moment) + 1)
            ),
        )
        return sorted(bookings, key=lambda booking: int(booking.starts_at))

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[BookingDocument]:
        return sorted(
            self._list_in_business(
                business_id, [field_equals(CONVERSATION_ID_FIELD, conversation_id)]
            ),
            key=lambda booking: int(booking.starts_at),
        )

    def count_made(
        self,
        business_id: BusinessId,
        period: ActivityPeriod,
    ) -> list[BookingActivityCount]:
        groups = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    excluding=(without_sandbox(),),
                    ranges=(period_range(CREATED_AT_FIELD, period),),
                ),
                group_by=(STATUS_FIELD,),
                buckets=timeline_buckets(CREATED_AT_FIELD, period),
            ),
        )
        return [
            BookingActivityCount(
                status=status,
                segment=segment_of(group),
                count=PeriodItemCount(int(group.count)),
            )
            for group in groups
            if (status := parse_choice(BookingStatus, group.values[0])) is not None
        ]


class LeadListing(BusinessScopedRepository[LeadDocument]):
    """Keyset pages and counts of a business's leads."""

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        status: LeadStatus | None,
        include_sandbox: IsSandboxIncluded,
    ) -> list[LeadDocument]:
        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            DocumentFilter(
                matches=() if status is None else (field_equals(STATUS_FIELD, status),),
                excluding=sandbox_exclusion(include_sandbox),
            ),
        )

    def count_by_status(
        self,
        business_id: BusinessId,
        include_sandbox: IsSandboxIncluded,
    ) -> dict[LeadStatus, ListItemCount]:
        counts: dict[LeadStatus, ListItemCount] = {}
        for group in self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(excluding=sandbox_exclusion(include_sandbox)),
                group_by=(STATUS_FIELD,),
            ),
        ):
            status: LeadStatus | None = parse_choice(LeadStatus, group.values[0])
            if status is not None:
                counts[status] = ListItemCount(int(group.count))

        return counts

    def count_made(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> PeriodItemCount:
        return period_count(
            self._aggregate_in_business(
                business_id,
                DocumentAggregation(
                    where=DocumentFilter(
                        excluding=(without_sandbox(),),
                        ranges=(time_range(CREATED_AT_FIELD, start, end),),
                    )
                ),
            )
        )

    def list_by_conversation(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> list[LeadDocument]:
        leads: Sequence[LeadDocument] = self._list_in_business(
            business_id, [field_equals(CONVERSATION_ID_FIELD, conversation_id)]
        )
        return sorted(leads, key=lambda lead: int(lead.created_at), reverse=True)
