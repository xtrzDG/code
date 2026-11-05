"""
The model tool send_payment_link: what the model may name (which of the
customer's own bookings or banquet requests, nothing else), what the server
adds, and what came of it. The amount and the link are never the model's:
the policy counts the amount, the owner's page is the link.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deposits import (
    DepositExemption,
    DepositSubject,
    PaymentLinkOutcome,
)
from app.schemas.dto.deposits.deposit_amounts import DepositAmount, IssuedDepositLine
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deposits.constrained_strings import DepositReference
from app.schemas.typings.deposits.strings import DepositHoldEndText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedMoneyText


class SendPaymentLinkToolInput(ImmutableDTO):
    """
    send_payment_link: the booking or the banquet request the deposit is
    for; neither means the latest one made in this conversation.
    """

    booking_id: BookingId | None = None
    lead_id: LeadId | None = None


class SendPaymentLinkCommand(ImmutableDTO):
    """The tool's input with the server-side context of the conversation."""

    business_id: BusinessId
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    source_channel: ChannelKind
    language: LanguageTag
    is_sandbox: IsSandboxConversation = False
    booking_id: BookingId | None = None
    lead_id: LeadId | None = None


class PaymentLinkReceipt(ImmutableDTO):
    """
    What send_payment_link did. SENT carries the payment line the reply
    gets under it (`issued`), the amount in the customer's language and
    until when the place or the link holds, in the business's time.
    """

    outcome: PaymentLinkOutcome
    subject: DepositSubject | None = None
    booking_id: BookingId | None = None
    lead_id: LeadId | None = None
    exemption: DepositExemption | None = None
    amount: DepositAmount | None = None
    amount_text: FormattedMoneyText | None = None
    held_until_text: DepositHoldEndText | None = None
    reference: DepositReference | None = None
    issued: IssuedDepositLine | None = None


class DepositQuoteQuery(ImmutableDTO):
    """Whether a booking or a banquet request just made needs a deposit."""

    business_id: BusinessId
    booking_id: BookingId | None = None
    lead_id: LeadId | None = None


class DepositQuote(ImmutableDTO):
    """A deposit is asked (`amount`), or not (`exemption` says why)."""

    amount: DepositAmount | None = None
    exemption: DepositExemption | None = None
