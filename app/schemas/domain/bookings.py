from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    BookingValueMinor,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId


class BookingStatusChange(PersistentDocument):
    """
    The last status change staff made in the cabinet (`changed_by`, at
    `changed_at`, UTC microseconds), from `previous_status`: what an Undo
    restores within its window.
    """

    previous_status: BookingStatus
    changed_at: Microseconds
    changed_by: UserId


class BookingDocument(BaseDocument):
    """
    Booking of a resource (concept table `bookings`); times are UTC.

    A booking of a service, package or room type names it
    (`service_item_id`) and keeps what it was booked with: the
    `buffer_minutes` its resource stays blocked after `ends_at`, and its
    value (`value_minor` in `currency_code`: the service price, or the
    nightly rates of the stay's nights). Without a priced item the value
    is unknown (None).

    `last_status_change` is the last status change staff made in the
    cabinet, which they may undo for a short while; any other change of
    the status (the customer cancelling, an undo) clears it.
    """

    # 2: `service_item_id`, `buffer_minutes`, `value_minor` and
    # `currency_code` (optional). 3: `last_status_change` (optional).
    schema_version: SchemaVersion = SchemaVersion("3")
    id: BookingId = Field(default_factory=BookingId)
    business_id: BusinessId
    resource_id: ResourceId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    party_size: PartySize
    status: BookingStatus = BookingStatus.CONFIRMED
    source_channel: ChannelKind
    notes: BookingNote | None = None
    is_sandbox: IsSandboxConversation = False
    # When the customer's reminder went out (UTC microseconds); None = not yet.
    reminder_sent_at: Microseconds | None = None
    # The customer's language when the booking was made (texts about it).
    language: LanguageTag | None = None
    service_item_id: KnowledgeItemId | None = None
    buffer_minutes: BufferMinutes | None = None
    value_minor: BookingValueMinor | None = None
    currency_code: CurrencyCode | None = None
    last_status_change: BookingStatusChange | None = None


class LeadDocument(BaseDocument):
    """Request for a manager (concept table `leads`)."""

    id: LeadId = Field(default_factory=LeadId)
    business_id: BusinessId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    lead_type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    source_channel: ChannelKind
    status: LeadStatus = LeadStatus.NEW
    is_sandbox: IsSandboxConversation = False
