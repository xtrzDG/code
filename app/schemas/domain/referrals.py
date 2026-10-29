from base_pydantic_schemas import BaseDocument, PersistentDocument
from typed_time_provider import Microseconds

from app.schemas.constants.referrals import CommissionStatus, ReferralCodeOwnerKind
from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.referrals.constrained_integers import (
    CommissionRateBasisPoints,
)
from app.schemas.typings.referrals.constrained_strings import (
    CommissionMonth,
    PayoutReference,
)
from app.schemas.typings.referrals.prefixed_id import (
    CommissionEntryId,
    PartnerId,
    ReferralCodeId,
    ReferralId,
)
from app.schemas.typings.users.prefixed_id import UserId


class BusinessReferral(PersistentDocument):
    """
    Who brought a business (`BusinessDocument.referred_by`): the code its
    owner signed up by and whose it is, a partner (commission on every
    paid invoice) or another business (a month of credit for both after
    the first payment). Set once, when the business is created.
    """

    code: ReferralCode
    owner_kind: ReferralCodeOwnerKind
    partner_id: PartnerId | None = None
    referring_business_id: BusinessId | None = None
    referred_at: Microseconds


class ReferralCodeDocument(BaseDocument):
    """
    A referral code and whose it is (a platform collection, migration
    1150): a partner's (any number, named by the platform team) or a
    business's own (one, derived from the business, shown in its
    invitations and "Powered by" links). The id derives from the code in
    lower case, so codes differing only in case are one code.

    `business_id` is the referring business of a BUSINESS code (the row
    belongs to it, so its owner reads it in the business's own scope);
    None for a partner's code.
    """

    id: ReferralCodeId
    code: ReferralCode
    owner_kind: ReferralCodeOwnerKind
    partner_id: PartnerId | None = None
    business_id: BusinessId | None = None


class ReferralDocument(BaseDocument):
    """
    A business that signed up by a code (a platform collection, migration
    1150): the partner's businesses (their portal) and the businesses an
    owner invited (the invitation card's counts). The id derives from the
    referred business: it is referred once.

    `business_id` is the referring business when an owner invited it (the
    row belongs to that business, whose owner counts it), None when a
    partner brought it. `first_paid_at` is when the referred business paid
    its first invoice; `rewarded_at` when both businesses got their month
    of credit for it (business referrals only).
    """

    id: ReferralId
    business_id: BusinessId | None = None
    referred_business_id: BusinessId
    code: ReferralCode
    owner_kind: ReferralCodeOwnerKind
    partner_id: PartnerId | None = None
    referred_at: Microseconds
    first_paid_at: Microseconds | None = None
    rewarded_at: Microseconds | None = None


class CommissionEntryDocument(BaseDocument):
    """
    A partner's commission on one paid invoice of a business they brought
    (a platform collection, migration 1150; the row belongs to the paying
    business). The id derives from the invoice: an invoice earns once.

    `base_minor` is what the invoice charged before tax, `amount_minor`
    the partner's share of it at the partner's rate of that moment, in
    the invoice's currency. `month` (UTC) is when it was earned and the
    payout it belongs to; the platform team marks a partner's month PAID
    with when, who and how (`payout_reference`).
    """

    id: CommissionEntryId
    partner_id: PartnerId
    business_id: BusinessId
    invoice_id: InvoiceId
    base_minor: MoneyAmountMinor
    rate_basis_points: CommissionRateBasisPoints
    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode
    accrued_at: Microseconds
    month: CommissionMonth
    status: CommissionStatus = CommissionStatus.ACCRUED
    paid_at: Microseconds | None = None
    paid_by: UserId | None = None
    payout_reference: PayoutReference | None = None
