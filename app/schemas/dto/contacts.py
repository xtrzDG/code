"""Cabinet customers (contacts): the list for data requests and one contact."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus, LeadStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.booleans import IsContactPhoneVerified
from app.schemas.typings.contacts.constrained_integers import (
    ContactBookingCount,
    ContactConversationCount,
    ContactLeadCount,
)
from app.schemas.typings.contacts.constrained_strings import ContactSearchText
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class ContactListQuery(ImmutableDTO):
    """
    Owner looks for customers, most recently active first.

    `search` matches part of the name (any case), the digits of a phone
    number (at least three) or the exact contact id.
    """

    user_id: UserId
    business_id: BusinessId
    search: ContactSearchText | None = None
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class ContactQuery(ImmutableDTO):
    """Owner opens one customer."""

    user_id: UserId
    business_id: BusinessId
    contact_id: ContactId
    client_ip_address: ClientIpAddress | None = None


class ContactSummaryView(ImmutableDTO):
    """
    One customer in the list: how to recognise them and how active they are.

    `phone_number` is the phone a channel proved when there is one
    (`is_phone_verified`), otherwise the one the customer typed. Counts and
    channels leave out the owner's test chats. An erased customer
    (`erased_at`) has no name, phone or language left; their anonymous
    conversations and bookings still count. `opted_out_channels`: where the
    customer sent STOP; while any is listed they get no reminders, feedback
    requests or messages after a missed call.
    """

    id: ContactId
    name: ContactName | None = None
    phone_number: E164PhoneNumber | None = None
    is_phone_verified: IsContactPhoneVerified = False
    language: LanguageTag | None = None
    channels: list[ChannelKind] = Field(default_factory=list[ChannelKind])
    conversation_count: ContactConversationCount
    booking_count: ContactBookingCount
    lead_count: ContactLeadCount
    first_seen_at: Microseconds
    last_activity_at: Microseconds
    erased_at: Microseconds | None = None
    opted_out_channels: list[ChannelKind] = Field(default_factory=list[ChannelKind])


class ContactPage(ImmutableDTO):
    """One page of customers; `next_cursor` is None on the last page."""

    items: list[ContactSummaryView]
    next_cursor: PageCursor | None = None


class ContactConversationView(ImmutableDTO):
    """A conversation of the customer (test chats left out)."""

    id: ConversationId
    channel: ChannelKind
    status: ConversationStatus
    started_at: Microseconds
    last_message_at: Microseconds


class ContactBookingView(ImmutableDTO):
    """A booking of the customer (start in UTC seconds, as bookings use)."""

    id: BookingId
    starts_at: BookingStartsAtUnixSeconds
    status: BookingStatus
    created_at: Microseconds


class ContactLeadView(ImmutableDTO):
    """A request the customer left for a manager."""

    id: LeadId
    status: LeadStatus
    created_at: Microseconds


class ContactDetailView(ImmutableDTO):
    """One customer with their conversations, bookings and leads, newest first."""

    contact: ContactSummaryView
    conversations: list[ContactConversationView] = Field(
        default_factory=list[ContactConversationView]
    )
    bookings: list[ContactBookingView] = Field(default_factory=list[ContactBookingView])
    leads: list[ContactLeadView] = Field(default_factory=list[ContactLeadView])


class ContactActivity(ImmutableDTO):
    """
    Records of one customer: their conversations, bookings and leads (the
    owner's test chats and autotests left out).
    """

    conversations: list[ConversationDocument] = Field(
        default_factory=list[ConversationDocument]
    )
    bookings: list[BookingDocument] = Field(default_factory=list[BookingDocument])
    leads: list[LeadDocument] = Field(default_factory=list[LeadDocument])


class ContactActivityTotals(ImmutableDTO):
    """
    How active one customer was, counted by the database for a page of the
    list (test chats left out): records per kind, the channels they came
    through and the moment of the latest one (None without any).
    """

    conversation_count: ContactConversationCount = ContactConversationCount(0)
    booking_count: ContactBookingCount = ContactBookingCount(0)
    lead_count: ContactLeadCount = ContactLeadCount(0)
    channels: list[ChannelKind] = Field(default_factory=list[ChannelKind])
    latest_at: Microseconds | None = None
