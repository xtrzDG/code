"""The cabinet's search (Cmd/Ctrl+K): customers, conversations and bookings."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.dto.contacts import ContactSummaryView
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.search.constrained_strings import CabinetSearchText
from app.schemas.typings.users.prefixed_id import UserId


class BusinessSearchQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    text: CabinetSearchText
    client_ip_address: ClientIpAddress | None = None


class ConversationHit(ImmutableDTO):
    """A conversation of a customer the search found (or named by its id)."""

    id: ConversationId
    contact_id: ContactId
    contact_name: ContactName | None = None
    channel: ChannelKind
    status: ConversationStatus
    last_message_at: Microseconds


class BookingHit(ImmutableDTO):
    """A booking of a customer the search found (or named by its id)."""

    id: BookingId
    contact_id: ContactId
    contact_name: ContactName | None = None
    starts_at: BookingStartsAtUnixSeconds
    status: BookingStatus
    party_size: PartySize
    source_channel: ChannelKind


class BusinessSearchResults(ImmutableDTO):
    """
    The hits, grouped: customers (exact matches first, then the most
    recently active), their latest conversations and their bookings (the
    latest start first), at most a few of each. Phones are masked for staff
    the owner did not allow to see them.
    """

    customers: list[ContactSummaryView] = Field(
        default_factory=list[ContactSummaryView]
    )
    conversations: list[ConversationHit] = Field(default_factory=list[ConversationHit])
    bookings: list[BookingHit] = Field(default_factory=list[BookingHit])
