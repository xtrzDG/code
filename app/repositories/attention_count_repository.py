"""Indexed counts of the waiting items of a business (navigation badges)."""

from collections.abc import Sequence

from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.attention_repositories import (
    AttentionCountRepoContract,
)
from app.repositories.document_queries import field_equals, of_business
from app.schemas.constants.bookings import BookingStatus, LeadStatus
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFieldRange
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import DocumentFieldText

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
IS_SANDBOX_FIELD: DocumentFieldPath = DocumentFieldPath("is_sandbox")
STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")
# `is_sandbox` as storage keeps it (the JSON text of the boolean).
NOT_SANDBOX: DocumentFieldMatch = DocumentFieldMatch(
    field=IS_SANDBOX_FIELD, value=DocumentFieldText("false")
)
OPEN_HANDOFF_STATUSES: tuple[HandoffStatus, ...] = tuple(
    status for status in HandoffStatus if status is not HandoffStatus.RESOLVED
)
MICROSECONDS_PER_SECOND: int = 1_000_000


class AttentionCountRepository(AttentionCountRepoContract):
    """
    Each count matches the business and a status (one index of the
    business and status, see migration 1040), narrowed to real activity by
    `is_sandbox`; unconfirmed bookings also by their start time.
    """

    def __init__(
        self,
        handoff_collection: DocumentCollectionAdapterContract[HandoffDocument],
        lead_collection: DocumentCollectionAdapterContract[LeadDocument],
        booking_collection: DocumentCollectionAdapterContract[BookingDocument],
        channel_collection: DocumentCollectionAdapterContract[ChannelDocument],
    ) -> None:
        self._handoffs: DocumentCollectionAdapterContract[HandoffDocument] = (
            handoff_collection
        )
        self._leads: DocumentCollectionAdapterContract[LeadDocument] = lead_collection
        self._bookings: DocumentCollectionAdapterContract[BookingDocument] = (
            booking_collection
        )
        self._channels: DocumentCollectionAdapterContract[ChannelDocument] = (
            channel_collection
        )

    def count_open_handoffs(self, business_id: BusinessId) -> ListItemCount:
        return ListItemCount(
            sum(
                count_with_status(self._handoffs, business_id, status, NOT_SANDBOX)
                for status in OPEN_HANDOFF_STATUSES
            )
        )

    def count_new_leads(self, business_id: BusinessId) -> ListItemCount:
        return ListItemCount(
            count_with_status(self._leads, business_id, LeadStatus.NEW, NOT_SANDBOX)
        )

    def count_unconfirmed_bookings(
        self,
        business_id: BusinessId,
        starting_from: Microseconds,
    ) -> ListItemCount:
        # Bookings keep their start in UNIX seconds.
        first_second: int = -(-int(starting_from) // MICROSECONDS_PER_SECOND)
        upcoming = DocumentFieldRange(
            field=STARTS_AT_FIELD, lower=DocumentFieldInteger(first_second)
        )
        return ListItemCount(
            count_with_status(
                self._bookings,
                business_id,
                BookingStatus.PENDING,
                NOT_SANDBOX,
                within=upcoming,
            )
        )

    def count_failing_channels(self, business_id: BusinessId) -> ListItemCount:
        return ListItemCount(
            count_with_status(self._channels, business_id, ChannelStatus.ERROR)
        )


def count_with_status[Document: PersistentDocument](
    collection: DocumentCollectionAdapterContract[Document],
    business_id: BusinessId,
    status: object,
    *extra: DocumentFieldMatch,
    within: DocumentFieldRange | None = None,
) -> int:
    matches: Sequence[DocumentFieldMatch] = (
        of_business(business_id),
        field_equals(STATUS_FIELD, status),
        *extra,
    )
    return int(collection.count_by_fields(matches, within))
