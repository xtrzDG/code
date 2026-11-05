"""Indexed counts of the value model beyond the dashboard's own."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.value_repositories import ValueCountRepoContract
from app.repositories.aggregate_reading import parse_choice
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_among,
    field_equals,
    of_business,
    time_range,
    without_sandbox,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import (
    DocumentFieldAmong,
    DocumentFieldRange,
    DocumentFilter,
)
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")
CONVERSATION_ID_FIELD: DocumentFieldPath = DocumentFieldPath("conversation_id")
AUTHOR_FIELD: DocumentFieldPath = DocumentFieldPath("author")


class ValueCountRepository(ValueCountRepoContract):
    """
    Grouped counts over indexed columns (no document is read): bookings by
    creation time without a conversation (`doc_conversation_id is null`),
    bookings by start time, and the assistant's messages by author and
    time (`(business_id, doc_author, doc_created_at)`, migration 1042).
    """

    def __init__(
        self,
        booking_collection: DocumentCollectionAdapterContract[BookingDocument],
        message_collection: DocumentCollectionAdapterContract[MessageDocument],
    ) -> None:
        self._bookings: DocumentCollectionAdapterContract[BookingDocument] = (
            booking_collection
        )
        self._messages: DocumentCollectionAdapterContract[MessageDocument] = (
            message_collection
        )

    def count_bookings_made_by_staff(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> dict[BookingStatus, PeriodItemCount]:
        return by_status(
            self._bookings.count_by(
                DocumentAggregation(
                    where=DocumentFilter(
                        matches=(of_business(business_id),),
                        excluding=(without_sandbox(),),
                        ranges=(time_range(CREATED_AT_FIELD, start, end),),
                        missing=(CONVERSATION_ID_FIELD,),
                    ),
                    group_by=(STATUS_FIELD,),
                )
            )
        )

    def count_assistant_replies(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
        conversation_ids: Sequence[ConversationId] | None = None,
    ) -> PeriodItemCount:
        among: tuple[DocumentFieldAmong, ...] = (
            ()
            if conversation_ids is None
            else (field_among(CONVERSATION_ID_FIELD, conversation_ids),)
        )
        groups: list[DocumentGroupCount] = self._messages.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(
                        of_business(business_id),
                        field_equals(AUTHOR_FIELD, MessageAuthor.ASSISTANT),
                    ),
                    among=among,
                    ranges=(time_range(CREATED_AT_FIELD, start, end),),
                )
            )
        )
        return PeriodItemCount(sum(int(group.count) for group in groups))

    def count_bookings_starting(
        self,
        business_id: BusinessId,
        starts_from: BookingSearchBoundSeconds,
        starts_before: BookingSearchBoundSeconds,
    ) -> dict[BookingStatus, PeriodItemCount]:
        return by_status(
            self._bookings.count_by(
                DocumentAggregation(
                    where=DocumentFilter(
                        matches=(of_business(business_id),),
                        excluding=(without_sandbox(),),
                        ranges=(
                            DocumentFieldRange(
                                field=STARTS_AT_FIELD,
                                lower=DocumentFieldInteger(int(starts_from)),
                                upper=DocumentFieldInteger(int(starts_before)),
                            ),
                        ),
                    ),
                    group_by=(STATUS_FIELD,),
                )
            )
        )


def by_status(groups: list[DocumentGroupCount]) -> dict[BookingStatus, PeriodItemCount]:
    """Booking counts by status (statuses of a newer release left out)."""

    counts: dict[BookingStatus, PeriodItemCount] = {}
    for group in groups:
        status: BookingStatus | None = parse_choice(BookingStatus, group.values[0])
        if status is not None:
            counts[status] = PeriodItemCount(
                int(counts.get(status, 0)) + int(group.count)
            )

    return counts
