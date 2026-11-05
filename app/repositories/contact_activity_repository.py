"""A customer's conversations, bookings and leads, by the customer (1122)."""

from collections import defaultdict
from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.contact_activity_repositories import (
    ContactActivityRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.conversation_lookup_fields import (
    CONTACT_ID_FIELD,
    LAST_MESSAGE_AT_FIELD,
)
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    descending,
    field_among,
    field_equals,
    of_business,
    without_sandbox,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.contacts import ContactActivity, ContactActivityTotals
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.constrained_integers import (
    ContactBookingCount,
    ContactConversationCount,
    ContactLeadCount,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CHANNEL_FIELD: DocumentFieldPath = DocumentFieldPath("channel")
SOURCE_CHANNEL_FIELD: DocumentFieldPath = DocumentFieldPath("source_channel")


class ContactActivityRepository(ContactActivityRepoContract):
    """
    Grouped counts per customer and channel over the indexed `contact_id`
    columns of conversations (1010), bookings and leads (1122), and the
    records of one customer through the same columns; never a whole
    business's history.
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

    def count_for_contacts(
        self,
        business_id: BusinessId,
        contact_ids: Sequence[ContactId],
    ) -> dict[ContactId, ContactActivityTotals]:
        if not contact_ids:
            return {}

        where = DocumentFilter(
            matches=(of_business(business_id),),
            among=(field_among(CONTACT_ID_FIELD, contact_ids),),
            excluding=(without_sandbox(),),
        )
        tallies: defaultdict[ContactId, ContactTally] = defaultdict(ContactTally)
        grouped: list[tuple[str, list[DocumentGroupCount]]] = [
            (
                "conversation",
                self._conversations.count_by(
                    by_contact(where, CHANNEL_FIELD, LAST_MESSAGE_AT_FIELD)
                ),
            ),
            (
                "booking",
                self._bookings.count_by(
                    by_contact(where, SOURCE_CHANNEL_FIELD, CREATED_AT_FIELD)
                ),
            ),
            (
                "lead",
                self._leads.count_by(
                    by_contact(where, SOURCE_CHANNEL_FIELD, CREATED_AT_FIELD)
                ),
            ),
        ]
        for kind, groups in grouped:
            for group in groups:
                if group.values[0] is not None:
                    tallies[ContactId(str(group.values[0]))].add(kind, group)

        return {contact_id: tally.totals() for contact_id, tally in tallies.items()}

    def list_for_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> ContactActivity:
        matches = (of_business(business_id), field_equals(CONTACT_ID_FIELD, contact_id))
        conversations = self._conversations.list_by_fields(
            matches, order=descending(LAST_MESSAGE_AT_FIELD)
        )
        bookings = self._bookings.list_by_fields(matches)
        leads = self._leads.list_by_fields(matches)
        return ContactActivity(
            conversations=[item for item in conversations if not item.is_sandbox],
            bookings=[item for item in bookings if not item.is_sandbox],
            leads=[item for item in leads if not item.is_sandbox],
        )


def by_contact(
    where: DocumentFilter,
    channel_field: DocumentFieldPath,
    moment_field: DocumentFieldPath,
) -> DocumentAggregation:
    """Counts per customer and channel, with the latest moment of each."""

    return DocumentAggregation(
        where=where,
        group_by=(CONTACT_ID_FIELD, channel_field),
        latest_of=moment_field,
    )


class ContactTally:
    """The groups of one customer added up."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {"conversation": 0, "booking": 0, "lead": 0}
        self.channels: set[ChannelKind] = set()
        self.latest_at: int | None = None

    def add(self, kind: str, group: DocumentGroupCount) -> None:
        self.counts[kind] += int(group.count)
        channel: ChannelKind | None = parse_choice(ChannelKind, group.values[1])
        if channel is not None and channel is not ChannelKind.OWNER_TEST:
            self.channels.add(channel)
        if group.latest is not None:
            self.latest_at = max(self.latest_at or 0, int(group.latest))

    def totals(self) -> ContactActivityTotals:
        return ContactActivityTotals(
            conversation_count=ContactConversationCount(self.counts["conversation"]),
            booking_count=ContactBookingCount(self.counts["booking"]),
            lead_count=ContactLeadCount(self.counts["lead"]),
            channels=sorted(self.channels, key=lambda channel: channel.value),
            latest_at=None if self.latest_at is None else Microseconds(self.latest_at),
        )
