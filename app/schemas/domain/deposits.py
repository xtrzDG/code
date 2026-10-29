"""
Deposits and prepayment links (W19-DEPOSITS, migration 1190): what a
business asks before it holds a booking or a banquet, where its customers
pay, and each deposit asked.
"""

from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deposits import (
    DepositRule,
    DepositStatus,
    DepositSubject,
    DepositTarget,
    PaymentLinkKind,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId, ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deposits.booleans import AreDepositsEnabled
from app.schemas.typings.deposits.constrained_integers import (
    DepositAmountMinor,
    DepositDueMinor,
    DepositHoldMinutes,
    DepositPercent,
    DepositRefundCutoffHours,
)
from app.schemas.typings.deposits.constrained_strings import (
    DepositReference,
    PaymentLinkAddress,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.prefixed_id import (
    DepositRequestId,
    DepositSettingsId,
    PaymentLinkId,
)
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId

DEFAULT_DEPOSIT_HOLD_MINUTES: DepositHoldMinutes = DepositHoldMinutes(60)
DEFAULT_REFUND_CUTOFF_HOURS: DepositRefundCutoffHours = DepositRefundCutoffHours(24)


class BookingDepositPolicy(PersistentDocument):
    """
    What a deposit asks: a fixed `amount_minor` for the booking (FIXED) or
    for each guest (PER_GUEST) in `currency_code`, the business currency, or
    a `percent` of the booking's value (PERCENT_OF_VALUE). It applies from
    `min_party_size` guests (None: every booking). The customer pays on the
    fixed page `payment_link_id` names, else on the business's template.
    The rule decides which of `amount_minor` and `percent` counts; the
    cabinet's input (`DepositPolicyInput`) accepts only the one it needs.
    """

    rule: DepositRule
    amount_minor: DepositAmountMinor | None = None
    percent: DepositPercent | None = None
    currency_code: CurrencyCode
    min_party_size: PartySize | None = None
    payment_link_id: PaymentLinkId | None = None


class TargetedDepositPolicy(PersistentDocument):
    """
    A policy and what it applies to: one resource (`resource_id`), one
    service, package or room type (`service_item_id`), or the banquet
    requests (no id); the target decides which id counts.
    """

    target: DepositTarget
    resource_id: ResourceId | None = None
    service_item_id: KnowledgeItemId | None = None
    policy: BookingDepositPolicy


class PaymentLink(PersistentDocument):
    """
    One of the owner's own payment pages (Flitt, Stripe, TBC, a bank): a
    fixed page or a template with {amount}, {amount_minor}, {currency} and
    {reference}. An address that carries a key (a token, a signature in
    its query) is kept only sealed with the platform key ring
    (`sealed_address`) and the cabinet sees its `preview`; any other is
    kept as entered (`address`). A sealed address wins when both are set.
    """

    id: PaymentLinkId = Field(default_factory=PaymentLinkId)
    label: PaymentLinkLabel
    kind: PaymentLinkKind
    address: PaymentLinkAddress | None = None
    sealed_address: EncryptedChannelSecret | None = None
    host: PaymentLinkHost
    preview: PaymentLinkPreview
    added_at: Microseconds


class RetiredPaymentLink(PersistentDocument):
    """
    A payment page the owner removed (`retired_at`), kept out of their list
    so that the deposits already asked on it keep their link: sent again,
    reminded of. It goes for good once no hold can still need it (the
    longest hold after `retired_at`).
    """

    link: PaymentLink
    retired_at: Microseconds


class DepositSettingsDocument(BaseDocument):
    """
    The deposits of one business (one document, the id derived from it):
    off until the owner turns them on (`enabled_at`: the first time they
    did, which the report's no-show rates before and after split on). A
    booking a policy covers waits `hold_minutes` for its deposit before its
    place is released; a paid booking cancelled at least
    `refund_cutoff_hours` before its start gets the deposit back (staff
    refund it in their merchant account). The policies of resources,
    services and banquets live here, edited on their cards; a policy naming
    no page uses `default_payment_link_id`. Pages the owner removed while
    deposits may still wait on them are `retired_payment_links`.
    """

    # 2: `retired_payment_links` and `enabled_at` (optional; a page removed
    # before kept no deposit's link, and the first turn-on was not noted).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: DepositSettingsId
    business_id: BusinessId
    is_enabled: AreDepositsEnabled = False
    hold_minutes: DepositHoldMinutes = DEFAULT_DEPOSIT_HOLD_MINUTES
    refund_cutoff_hours: DepositRefundCutoffHours = DEFAULT_REFUND_CUTOFF_HOURS
    payment_links: list[PaymentLink] = Field(default_factory=list[PaymentLink])
    default_payment_link_id: PaymentLinkId | None = None
    policies: list[TargetedDepositPolicy] = Field(
        default_factory=list[TargetedDepositPolicy]
    )
    retired_payment_links: list[RetiredPaymentLink] = Field(
        default_factory=list[RetiredPaymentLink]
    )
    enabled_at: Microseconds | None = None
    updated_by: UserId | None = None


class BookingDeposit(PersistentDocument):
    """
    The deposit of a booking as its list shows it: the request, its state,
    the amount and, while it waits, when the held place is released.
    """

    request_id: DepositRequestId
    status: DepositStatus
    amount_minor: DepositDueMinor
    currency_code: CurrencyCode
    hold_expires_at: Microseconds | None = None


class DepositRequestDocument(BaseDocument):
    """
    One deposit asked of a customer for a booking (`booking_id`) or a
    banquet request (`lead_id`), in the chat where they asked
    (`conversation_id`, `source_channel`, `language`): `amount_minor` in
    `currency_code`, paid on the page `payment_link_id` under `reference`.

    AWAITING until staff mark it PAID (`paid_at`, `marked_paid_by`), or
    until `hold_expires_at` passes (EXPIRED: the booking is released). A
    reminder goes once at `reminder_due_at`. When a paid booking is
    cancelled (`cancelled_at`) or its guest does not come, its fate
    (REFUND_DUE or KEPT) is decided at `settle_after`, after the cabinet's
    undo window for a staff change; `settled_at` is when it was.
    """

    id: DepositRequestId = Field(default_factory=DepositRequestId)
    business_id: BusinessId
    subject: DepositSubject
    booking_id: BookingId | None = None
    lead_id: LeadId | None = None
    contact_id: ContactId
    conversation_id: ConversationId | None = None
    source_channel: ChannelKind
    language: LanguageTag
    amount_minor: DepositDueMinor
    currency_code: CurrencyCode
    reference: DepositReference
    payment_link_id: PaymentLinkId
    status: DepositStatus = DepositStatus.AWAITING
    requested_at: Microseconds
    hold_expires_at: Microseconds
    reminder_due_at: Microseconds | None = None
    reminder_sent_at: Microseconds | None = None
    paid_at: Microseconds | None = None
    marked_paid_by: UserId | None = None
    cancelled_at: Microseconds | None = None
    settle_after: Microseconds | None = None
    settled_at: Microseconds | None = None
    is_sandbox: IsSandboxConversation = False
