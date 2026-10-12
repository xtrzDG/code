"""A deposit as staff see it, and what they do with it."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deposits import DepositStatus, DepositSubject
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.deposits.constrained_strings import (
    DepositReference,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId


class DepositRequestView(ImmutableDTO):
    """
    One deposit asked: of which booking or banquet request, how much, under
    which reference and page, its state, and when it was asked, is held
    until, was paid (and by whose mark) or is to be refunded.
    """

    id: DepositRequestId
    subject: DepositSubject
    booking_id: BookingId | None = None
    lead_id: LeadId | None = None
    contact_id: ContactId
    source_channel: ChannelKind
    status: DepositStatus
    amount_minor: DepositDueMinor
    currency_code: CurrencyCode
    reference: DepositReference
    payment_link_label: PaymentLinkLabel | None = None
    requested_at: Microseconds
    hold_expires_at: Microseconds
    reminder_sent_at: Microseconds | None = None
    paid_at: Microseconds | None = None
    marked_paid_by: UserId | None = None
    cancelled_at: Microseconds | None = None
    settled_at: Microseconds | None = None


class DepositRequestQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request_id: DepositRequestId


class MarkDepositPaidCommand(ImmutableDTO):
    """Staff saw the money in their merchant account: the deposit is paid."""

    user_id: UserId
    business_id: BusinessId
    request_id: DepositRequestId
