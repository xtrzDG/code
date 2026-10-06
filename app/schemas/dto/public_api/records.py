"""
Bookings, leads and customers as the public API and webhooks show them
(`/v1/public-api/*`, frozen within /v1: docs/api-versioning.md). Moments
are ISO 8601 (`PublicTimestamp`); a booking's start and end carry the
business's own offset, everything else is UTC.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.bookings import BookingStatus, LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.constrained_integers import (
    BookingValueMinor,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
    ResourceName,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.integrations.constrained_strings import PublicTimestamp
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag


class PublicMoney(ImmutableDTO):
    """An amount in minor units (cents, tetri) of its ISO 4217 currency."""

    amount_minor: BookingValueMinor
    currency: CurrencyCode


class PublicContactRef(ImmutableDTO):
    """The customer a record is about (empty name and phone once erased)."""

    id: ContactId
    name: ContactName | None = None
    phone_number: E164PhoneNumber | None = None


class PublicResourceRef(ImmutableDTO):
    """The table, room, specialist or other resource a booking takes."""

    id: ResourceId
    name: ResourceName


class PublicServiceRef(ImmutableDTO):
    """The service, package or room type a booking is for."""

    id: KnowledgeItemId
    name: KnowledgeTitle


class PublicBooking(ImmutableDTO):
    """
    A booking: when (`starts_at`, `ends_at` with the business's offset, and
    its `timezone`), what (`resource`, `service`, `party_size`, `value`),
    for whom (`contact`) and where it came from (`source_channel`, and the
    tag of the link or ad that brought the customer, `acquisition_source`).
    """

    id: BookingId
    status: BookingStatus
    starts_at: PublicTimestamp
    ends_at: PublicTimestamp
    timezone: TimezoneName
    party_size: PartySize
    resource: PublicResourceRef | None = None
    service: PublicServiceRef | None = None
    value: PublicMoney | None = None
    notes: BookingNote | None = None
    contact: PublicContactRef
    source_channel: ChannelKind
    acquisition_source: AcquisitionSourceTag | None = None
    conversation_id: ConversationId | None = None
    created_at: PublicTimestamp
    updated_at: PublicTimestamp


class PublicLead(ImmutableDTO):
    """A request passed to the team (a banquet, a group, an order...)."""

    id: LeadId
    status: LeadStatus
    type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    contact: PublicContactRef
    source_channel: ChannelKind
    acquisition_source: AcquisitionSourceTag | None = None
    conversation_id: ConversationId | None = None
    created_at: PublicTimestamp
    updated_at: PublicTimestamp


class PublicContact(ImmutableDTO):
    """A customer of the business."""

    id: ContactId
    name: ContactName | None = None
    phone_number: E164PhoneNumber | None = None
    language: LanguageTag | None = None
    created_at: PublicTimestamp
    updated_at: PublicTimestamp
