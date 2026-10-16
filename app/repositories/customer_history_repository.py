"""What customers did across channels, read by customer (1122, 1140)."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.customer_repositories import (
    CustomerHistoryRepoContract,
)
from app.repositories.conversation_lookup_fields import (
    CONTACT_ID_FIELD,
    CONVERSATION_ID_FIELD,
    LAST_MESSAGE_AT_FIELD,
    STATUS_FIELD,
)
from app.repositories.document_queries import (
    field_among,
    of_business,
    without_sandbox,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.customers.customer_records import ContactVisits
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.constrained_integers import ContactVisitCount
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")
MICROSECONDS_PER_SECOND: int = 1_000_000
# Statuses of a booking that counts as a visit once it started.
VISIT_STATUSES: tuple[BookingStatus, ...] = (
    BookingStatus.CONFIRMED,
    BookingStatus.COMPLETED,
)
# The calls of one customer's phone conversations, at most (a page).
CALLS_LIMIT: DocumentQueryLimit = DocumentQueryLimit(200)


class CustomerHistoryRepository(CustomerHistoryRepoContract):
    """
    Visits counted by the database over the indexed `contact_id`, `status`
    and `starts_at` columns of bookings; calls by their conversations; the
    latest conversations and bookings of a few customers, a page each.
    """

    def __init__(
        self,
        conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ],
        booking_collection: DocumentCollectionAdapterContract[BookingDocument],
        call_collection: DocumentCollectionAdapterContract[CallDocument],
    ) -> None:
        self._conversations: DocumentCollectionAdapterContract[ConversationDocument] = (
            conversation_collection
        )
        self._bookings: DocumentCollectionAdapterContract[BookingDocument] = (
            booking_collection
        )
        self._calls: DocumentCollectionAdapterContract[CallDocument] = call_collection

    def visits_for_contacts(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
        before: Microseconds,
    ) -> dict[ContactId, ContactVisits]:
        if not contact_ids:
            return {}

        groups: list[DocumentGroupCount] = self._bookings.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(of_business(business_id),),
                    among=(
                        field_among(CONTACT_ID_FIELD, contact_ids),
                        field_among(STATUS_FIELD, VISIT_STATUSES),
                    ),
                    excluding=(without_sandbox(),),
                    ranges=(
                        DocumentFieldRange(
                            field=STARTS_AT_FIELD,
                            upper=DocumentFieldInteger(
                                int(before) // MICROSECONDS_PER_SECOND
                            ),
                        ),
                    ),
                ),
                group_by=(CONTACT_ID_FIELD,),
                latest_of=STARTS_AT_FIELD,
            )
        )
        return {
            ContactId(str(group.values[0])): ContactVisits(
                visit_count=ContactVisitCount(int(group.count)),
                last_visit_at=(
                    None
                    if group.latest is None
                    else Microseconds(int(group.latest) * MICROSECONDS_PER_SECOND)
                ),
            )
            for group in groups
            if group.values[0] is not None
        }

    def calls_of_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> list[CallDocument]:
        if not conversation_ids:
            return []

        calls: list[CallDocument] = self._calls.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(of_business(business_id),),
                    among=(field_among(CONVERSATION_ID_FIELD, conversation_ids),),
                ),
                sort_fields=(),
                limit=CALLS_LIMIT,
            )
        )
        return sorted(calls, key=lambda call: int(call.started_at), reverse=True)

    def latest_conversations_of(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        if not contact_ids:
            return []

        return self._conversations.page_by(
            DocumentPageQuery(
                where=by_contacts(business_id, contact_ids),
                sort_fields=(LAST_MESSAGE_AT_FIELD,),
                limit=limit,
            )
        )

    def latest_bookings_of(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
        limit: DocumentQueryLimit,
    ) -> list[BookingDocument]:
        if not contact_ids:
            return []

        return self._bookings.page_by(
            DocumentPageQuery(
                where=by_contacts(business_id, contact_ids),
                sort_fields=(STARTS_AT_FIELD,),
                limit=limit,
            )
        )


def by_contacts(
    business_id: BusinessId, contact_ids: Sequence[ContactId]
) -> DocumentFilter:
    return DocumentFilter(
        matches=(of_business(business_id),),
        among=(field_among(CONTACT_ID_FIELD, contact_ids),),
        excluding=(without_sandbox(),),
    )
