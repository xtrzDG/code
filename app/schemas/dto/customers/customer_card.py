"""Customers: the team's card on one customer (tags, VIP, block) and its standing."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.customers import CustomerStanding
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.booleans import (
    IsContactBlocked,
    IsContactErased,
    IsVipCustomer,
)
from app.schemas.typings.contacts.constrained_integers import (
    ContactBookingCount,
    ContactConversationCount,
    ContactVisitCount,
)
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.users.prefixed_id import UserId


class CustomerCardRequest(ImmutableDTO):
    """
    A change of the card: tags to add and to take off (any case), and the
    VIP flag (unchanged when left out). At most 20 tags at a time.
    """

    add_tags: list[CustomerTag] = Field(
        default_factory=list[CustomerTag], max_length=20
    )
    remove_tags: list[CustomerTag] = Field(
        default_factory=list[CustomerTag], max_length=20
    )
    is_vip: IsVipCustomer | None = None


class ChangeCustomerCardCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    contact_id: ContactId
    request: CustomerCardRequest
    client_ip_address: ClientIpAddress | None = None


class CustomerBlockingRequest(ImmutableDTO):
    """Block the customer (the assistant stops answering them) or unblock them."""

    is_blocked: IsContactBlocked


class ChangeCustomerBlockingCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    contact_id: ContactId
    request: CustomerBlockingRequest
    client_ip_address: ClientIpAddress | None = None


class CustomerCardView(ImmutableDTO):
    """
    The card after a change: the customer's tags, VIP flag and block, and
    the business's tags (the latest used first) to offer next.
    """

    contact_id: ContactId
    tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])
    is_vip: IsVipCustomer = False
    is_blocked: IsContactBlocked = False
    blocked_at: Microseconds | None = None
    known_tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])


class ContactStandingQuery(ImmutableDTO):
    """The conversation header asks how well the business knows its customer."""

    user_id: UserId
    business_id: BusinessId
    contact_id: ContactId


class ContactStandingView(ImmutableDTO):
    """
    "Regular customer · 4 visits": the standing (CustomerStanding), the
    visits and when the latest started, the conversations and bookings
    (test chats left out) and the card's flags. No personal data, so it is
    not audited.
    """

    contact_id: ContactId
    standing: CustomerStanding
    visit_count: ContactVisitCount
    last_visit_at: Microseconds | None = None
    conversation_count: ContactConversationCount
    booking_count: ContactBookingCount
    is_vip: IsVipCustomer = False
    is_blocked: IsContactBlocked = False
    is_erased: IsContactErased = False
