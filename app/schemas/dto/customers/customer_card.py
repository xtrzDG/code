"""
Customers: the team's card on one customer (tags, VIP, block, marketing
consent) and its standing.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.customers import CustomerStanding
from app.schemas.constants.marketing_consent import (
    MarketingConsentSource,
    MarketingConsentStatus,
    MarketingConsentText,
    MarketingConsentWithdrawal,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.booleans import (
    IsContactBlocked,
    IsContactErased,
    IsMarketingConsentGiven,
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
    A change of the card: tags to add and to take off (any case), the VIP
    flag, and the customer's marketing consent as they gave or took it back
    in person (true records the current wording with the team member who
    recorded it; false records that it was taken back); each unchanged
    when left out. At most 20 tags at a time.
    """

    add_tags: list[CustomerTag] = Field(
        default_factory=list[CustomerTag], max_length=20
    )
    remove_tags: list[CustomerTag] = Field(
        default_factory=list[CustomerTag], max_length=20
    )
    is_vip: IsVipCustomer | None = None
    marketing_consent: IsMarketingConsentGiven | None = None


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


class MarketingConsentView(ImmutableDTO):
    """
    The customer's marketing consent as the card shows it: the status
    (STOPPED whatever was recorded while they said STOP, are on the
    suppression list or blocked), and what was recorded: when, where, by
    whom (None: the customer), the wording's version, and when, how and by
    whom it was taken back.
    """

    status: MarketingConsentStatus = MarketingConsentStatus.NOT_GIVEN
    given_at: Microseconds | None = None
    source: MarketingConsentSource | None = None
    text_version: MarketingConsentText | None = None
    recorded_by: UserId | None = None
    withdrawn_at: Microseconds | None = None
    withdrawal: MarketingConsentWithdrawal | None = None
    withdrawn_by: UserId | None = None


class CustomerCardView(ImmutableDTO):
    """
    The card after a change: the customer's tags, VIP flag, block and
    marketing consent, and the business's tags (the latest used first) to
    offer next.
    """

    contact_id: ContactId
    tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])
    is_vip: IsVipCustomer = False
    is_blocked: IsContactBlocked = False
    blocked_at: Microseconds | None = None
    known_tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])
    marketing_consent: MarketingConsentView = Field(
        default_factory=MarketingConsentView
    )


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
