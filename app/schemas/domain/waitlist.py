from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.waitlist import WaitlistEndReason, WaitlistStatus
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    BookingValueMinor,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.knowledge.constrained_integers import BufferMinutes
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.waitlist.booleans import IsWaitlistEnabled
from app.schemas.typings.waitlist.constrained_integers import (
    WaitlistHoldMinutes,
    WaitlistOfferCount,
)
from app.schemas.typings.waitlist.prefixed_id import (
    WaitlistEntryId,
    WaitlistSettingsId,
)

DEFAULT_HOLD_MINUTES: WaitlistHoldMinutes = WaitlistHoldMinutes(30)


class WaitlistOffer(PersistentDocument):
    """
    The freed place held for a waiting customer: the resource and the time
    the cancelled (or moved) booking `freed_booking_id` gave up, with what
    that booking was (its service, the resource's rest after it, its
    value), so a "yes" books exactly that. Where the offer went:
    `channel`, the conversation that shows it and its outbox message
    (None for the website chat, where the conversation carries it).
    """

    freed_booking_id: BookingId
    resource_id: ResourceId
    starts_at: BookingStartsAtUnixSeconds
    ends_at: BookingEndsAtUnixSeconds
    buffer_minutes: BufferMinutes | None = None
    service_item_id: KnowledgeItemId | None = None
    value_minor: BookingValueMinor | None = None
    currency_code: CurrencyCode | None = None
    offered_at: Microseconds
    channel: ChannelKind | None = None
    conversation_id: ConversationId | None = None
    outbound_message_id: OutboundMessageId | None = None


class WaitlistEntryDocument(BaseDocument):
    """
    A customer's place on a business's waitlist: nothing was free when they
    asked, so the assistant noted what they want (the local `date`, a time
    window `time_from`–`time_to` or any time, the party, nights of a stay,
    a service, a named master or room, a kind of resource) in the chat
    where they asked (`conversation_id`, `source_channel`, `language`).

    When a cancellation or a move frees a place that fits, the first
    waiting entry (oldest first) is OFFERED it: the place is held for them
    until `offer_expires_at` (the business's hold) and the offer goes to
    their chat. A "yes" makes the place their booking (BOOKED,
    `booking_id`); a "no", silence past the hold, the day passing
    (`waits_until`, the end of that day in UTC) or staff ending it make it
    EXPIRED with its `end_reason`. Test chats' entries (`is_sandbox`) are
    never offered anything.
    """

    id: WaitlistEntryId = Field(default_factory=WaitlistEntryId)
    business_id: BusinessId
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
    service_item_id: KnowledgeItemId | None = None
    notes: BookingNote | None = None
    waits_until: Microseconds
    status: WaitlistStatus = WaitlistStatus.WAITING
    offer: WaitlistOffer | None = None
    offer_expires_at: Microseconds | None = None
    offer_count: WaitlistOfferCount = WaitlistOfferCount(0)
    booking_id: BookingId | None = None
    booked_at: Microseconds | None = None
    end_reason: WaitlistEndReason | None = None
    ended_at: Microseconds | None = None
    ended_by: UserId | None = None
    is_sandbox: IsSandboxConversation = False


class WaitlistSettingsDocument(BaseDocument):
    """
    The waitlist of one business (Bookings → Waitlist; one document per
    business, the id derived from it). On by default: when nothing is free
    the assistant offers to put the customer on the list, and a freed place
    is held for the first one who fits for `hold_minutes`.
    """

    id: WaitlistSettingsId
    business_id: BusinessId
    is_enabled: IsWaitlistEnabled = True
    hold_minutes: WaitlistHoldMinutes = DEFAULT_HOLD_MINUTES
    updated_by: UserId | None = None
