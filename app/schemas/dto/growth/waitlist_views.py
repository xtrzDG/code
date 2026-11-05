"""Bookings → Waitlist: the entries, their offers and the waitlist's settings."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.waitlist import (
    WaitlistEndReason,
    WaitlistListFilter,
    WaitlistStatus,
)
from app.schemas.dto.growth.growth_counts import WaitlistStatusCount
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote, ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.waitlist.booleans import IsWaitlistEnabled
from app.schemas.typings.waitlist.constrained_integers import (
    WaitlistHoldMinutes,
    WaitlistOfferCount,
)
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId


class WaitlistPageQuery(ImmutableDTO):
    """
    One page of the business's waitlist: still open (waiting or offered),
    booked, or ended; first come first for open ones, the latest first for
    the others. Staff and owners; customers' names, so audited.
    """

    user_id: UserId
    business_id: BusinessId
    list_filter: WaitlistListFilter = WaitlistListFilter.ACTIVE
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class WaitlistOfferView(ImmutableDTO):
    """The freed place held for the customer, in the business's local time."""

    resource_id: ResourceId
    resource_name: ResourceName | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    end_time: LocalTimeOfDay | None = None
    offered_at: Microseconds
    expires_at: Microseconds | None = None
    channel: ChannelKind | None = None
    freed_booking_id: BookingId


class WaitlistEntryView(ImmutableDTO):
    """
    One customer's place on the list: who (their name when known), what
    they want (date, time window, party, nights, service, resource), where
    they asked, where it stands and, while one is held, the offered place.
    """

    id: WaitlistEntryId
    contact_id: ContactId
    contact_name: ContactName | None = None
    conversation_id: ConversationId | None = None
    source_channel: ChannelKind
    language: LanguageTag
    date: LocalDate
    time_from: LocalTimeOfDay | None = None
    time_to: LocalTimeOfDay | None = None
    party_size: PartySize
    nights: NightCount | None = None
    resource_kind: ResourceKind | None = None
    resource_id: ResourceId | None = None
    resource_name: ResourceName | None = None
    service_item_id: KnowledgeItemId | None = None
    service_title: KnowledgeTitle | None = None
    notes: BookingNote | None = None
    status: WaitlistStatus
    end_reason: WaitlistEndReason | None = None
    offer: WaitlistOfferView | None = None
    offer_count: WaitlistOfferCount
    booking_id: BookingId | None = None
    booked_at: Microseconds | None = None
    created_at: Microseconds
    ended_at: Microseconds | None = None


class WaitlistEntryPage(ImmutableDTO):
    items: list[WaitlistEntryView]
    next_cursor: PageCursor | None = None
    timezone: TimezoneName


class RemoveWaitlistEntryCommand(ImmutableDTO):
    """Staff take a customer off the list (an offered place goes to the next)."""

    user_id: UserId
    business_id: BusinessId
    entry_id: WaitlistEntryId
    client_ip_address: ClientIpAddress | None = None


class WaitlistSettingsRequest(ImmutableDTO):
    """The owner's choices: keep a waitlist, and how long a freed place is held."""

    is_enabled: IsWaitlistEnabled = True
    hold_minutes: WaitlistHoldMinutes = WaitlistHoldMinutes(30)


class WaitlistSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateWaitlistSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: WaitlistSettingsRequest


class WaitlistSettingsView(ImmutableDTO):
    """The settings with how many real entries are in each status."""

    is_enabled: IsWaitlistEnabled
    hold_minutes: WaitlistHoldMinutes
    counts: list[WaitlistStatusCount] = Field(default_factory=list[WaitlistStatusCount])
