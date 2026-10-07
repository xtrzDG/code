"""The model tool join_waitlist: the customer's wish and what the list made of it."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.bookings.constrained_integers import NightCount, PartySize
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.strings import (
    BookingNote,
    ResourceName,
    ResourceReference,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.knowledge.strings import KnowledgeTitle, ServiceReference
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.waitlist.booleans import (
    IsAlreadyOnWaitlist,
    IsReachableOnlyInWebChat,
)
from app.schemas.typings.waitlist.constrained_integers import WaitlistHoldMinutes
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId

DEFAULT_PARTY_SIZE: PartySize = PartySize(1)


class JoinWaitlistCommand(ImmutableDTO):
    """
    Put a customer on the waitlist of a local date (model tool
    join_waitlist): business, contact, conversation, channel, language and
    the sandbox flag come from the server, the rest from the customer.
    """

    business_id: BusinessId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    contact_name: ContactName | None = None
    source_channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False
    date: LocalDate
    time_from: LocalTimeOfDay | None = None
    time_to: LocalTimeOfDay | None = None
    party_size: PartySize = DEFAULT_PARTY_SIZE
    nights: NightCount | None = None
    service_reference: ServiceReference | None = None
    resource_reference: ResourceReference | None = None
    resource_kind: ResourceKind | None = None
    notes: BookingNote | None = None


class WaitlistJoinReceipt(ImmutableDTO):
    """
    The customer's place on the list as the model tells them about it:
    the wish as stored, how long a freed place is held for them, whether
    they were already waiting for that day (their wish was updated), and
    whether only the website chat can reach them (no messenger known).
    """

    entry_id: WaitlistEntryId
    date: LocalDate
    time_from: LocalTimeOfDay | None = None
    time_to: LocalTimeOfDay | None = None
    party_size: PartySize
    nights: NightCount | None = None
    service_title: KnowledgeTitle | None = None
    resource_name: ResourceName | None = None
    hold_minutes: WaitlistHoldMinutes
    timezone: TimezoneName
    is_already_waiting: IsAlreadyOnWaitlist = False
    is_web_chat_only: IsReachableOnlyInWebChat = False
