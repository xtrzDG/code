"""Counts of a period per customer source (Reports, "Where customers came from")."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.value_repositories import CustomerSourceRepoContract
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import read_business_id
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    of_business,
    time_range,
    without_sandbox,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.dto.value.customer_sources import (
    ConversationBookingCount,
    ConversationLeadCount,
    ConversationOrigin,
    SourceConversationCount,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from app.schemas.typings.value.constrained_integers import BookedValueMinor

SOURCE_FIELD: DocumentFieldPath = DocumentFieldPath("acquisition_source")
CHANNEL_FIELD: DocumentFieldPath = DocumentFieldPath("channel")
CONVERSATION_ID_FIELD: DocumentFieldPath = DocumentFieldPath("conversation_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
CURRENCY_CODE_FIELD: DocumentFieldPath = DocumentFieldPath("currency_code")
VALUE_FIELD: DocumentFieldPath = DocumentFieldPath("value_minor")
# Conversations read per statement when their origins are looked up.
ORIGIN_BATCH_SIZE: int = 500


class CustomerSourceRepository(CustomerSourceRepoContract):
    """
    Grouped counts over indexed columns: conversations by creation time,
    source and channel (`conversations_doc_created_at_source_idx`, 1100);
    bookings and requests by creation time and conversation (1042, 1083).
    Only the origins of conversations with bookings or requests in the
    period are read as documents, in batches. Sandbox activity is left out.
    """

    def __init__(
        self,
        conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ],
        booking_collection: DocumentCollectionAdapterContract[BookingDocument],
        lead_collection: DocumentCollectionAdapterContract[LeadDocument],
    ) -> None:
        self._conversations: DocumentCollectionAdapterContract[ConversationDocument] = (
            conversation_collection
        )
        self._bookings: DocumentCollectionAdapterContract[BookingDocument] = (
            booking_collection
        )
        self._leads: DocumentCollectionAdapterContract[LeadDocument] = lead_collection

    def count_conversations_by_source(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> list[SourceConversationCount]:
        groups: list[DocumentGroupCount] = self._conversations.count_by(
            started_in(business_id, start, end, (SOURCE_FIELD, CHANNEL_FIELD))
        )
        return [
            SourceConversationCount(
                acquisition_source=read_source(group.values[0]),
                channel=channel,
                count=PeriodItemCount(int(group.count)),
            )
            for group in groups
            if (channel := parse_choice(ChannelKind, group.values[1])) is not None
        ]

    def count_bookings_by_conversation(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> list[ConversationBookingCount]:
        groups: list[DocumentGroupCount] = self._bookings.count_by(
            started_in(
                business_id,
                start,
                end,
                (CONVERSATION_ID_FIELD, STATUS_FIELD, CURRENCY_CODE_FIELD),
                totals_of=(VALUE_FIELD,),
            )
        )
        return [
            ConversationBookingCount(
                conversation_id=ConversationId(str(conversation)),
                status=status,
                currency_code=(
                    None if group.values[2] is None else CurrencyCode(group.values[2])
                ),
                count=PeriodItemCount(int(group.count)),
                value_minor=BookedValueMinor(int(group.totals[0])),
            )
            for group in groups
            if (conversation := group.values[0]) is not None
            and (status := parse_choice(BookingStatus, group.values[1])) is not None
        ]

    def count_leads_by_conversation(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> list[ConversationLeadCount]:
        groups: list[DocumentGroupCount] = self._leads.count_by(
            started_in(business_id, start, end, (CONVERSATION_ID_FIELD,))
        )
        return [
            ConversationLeadCount(
                conversation_id=ConversationId(str(conversation)),
                count=PeriodItemCount(int(group.count)),
            )
            for group in groups
            if (conversation := group.values[0]) is not None
        ]

    def find_origins(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> list[ConversationOrigin]:
        keys: list[str] = sorted(
            {str(conversation_id) for conversation_id in conversation_ids}
        )
        origins: list[ConversationOrigin] = []
        for first in range(0, len(keys), ORIGIN_BATCH_SIZE):
            origins.extend(
                ConversationOrigin(
                    conversation_id=conversation.id,
                    acquisition_source=conversation.acquisition_source,
                    channel=conversation.channel,
                )
                for conversation in self._conversations.get_many(
                    keys[first : first + ORIGIN_BATCH_SIZE]
                )
                if read_business_id(conversation) == business_id
            )

        return origins


def started_in(
    business_id: BusinessId,
    start: Microseconds,
    end: Microseconds,
    group_by: tuple[DocumentFieldPath, ...],
    totals_of: tuple[DocumentFieldPath, ...] = (),
) -> DocumentAggregation:
    """The business's documents created from `start` to `end`, sandbox left out."""

    return DocumentAggregation(
        where=DocumentFilter(
            matches=(of_business(business_id),),
            excluding=(without_sandbox(),),
            ranges=(time_range(CREATED_AT_FIELD, start, end),),
        ),
        group_by=group_by,
        totals_of=totals_of,
    )


def read_source(value: DocumentFieldText | None) -> AcquisitionSourceTag | None:
    """A stored source as its tag; None without one or for an unreadable one."""

    if value is None:
        return None

    try:
        return AcquisitionSourceTag(str(value))
    except ValueError:
        return None
