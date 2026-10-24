"""A partner's portal: their links, the businesses they brought, commissions."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.referrals import CommissionStatus, PartnerStatus
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.referrals.constrained_integers import (
    CommissionInvoiceCount,
    CommissionRateBasisPoints,
    ReferredBusinessCount,
)
from app.schemas.typings.referrals.constrained_strings import (
    CommissionMonth,
    PartnerName,
    ReferralLink,
)
from app.schemas.typings.referrals.prefixed_id import CommissionEntryId, PartnerId
from app.schemas.typings.users.prefixed_id import UserId


class PartnerPortalQuery(ImmutableDTO):
    """A signed-in partner opens their portal."""

    user_id: UserId


class PartnerPageQuery(ImmutableDTO):
    """One page of a partner's businesses or commissions, newest first."""

    user_id: UserId
    page: PageRequest = Field(default_factory=PageRequest)


class PartnerCodeView(ImmutableDTO):
    """One of the partner's codes and its link to the platform's site."""

    code: ReferralCode
    link: ReferralLink | None = None


class CommissionTotalView(ImmutableDTO):
    """Commissions in one currency and status: how many invoices, how much."""

    currency_code: CurrencyCode
    status: CommissionStatus
    invoice_count: CommissionInvoiceCount
    amount_minor: MoneyAmountMinor


class PartnerPortalView(ImmutableDTO):
    """
    The partner's portal: who they are to the platform, their rate, their
    codes with links (the cabinet adds the landing page and `src` the
    partner picks, and draws the QR code), how many businesses signed up by
    them and how many paid, and their commissions to be paid and paid.
    """

    partner_id: PartnerId
    name: PartnerName
    status: PartnerStatus
    commission_rate_basis_points: CommissionRateBasisPoints
    codes: list[PartnerCodeView] = Field(default_factory=list[PartnerCodeView])
    referred_businesses: ReferredBusinessCount
    paid_businesses: ReferredBusinessCount
    totals: list[CommissionTotalView] = Field(default_factory=list[CommissionTotalView])


class PartnerReferralView(ImmutableDTO):
    """
    A business the partner brought: its name, country, plan and state, the
    code it signed up by, and when it signed up and first paid. Nothing
    about its owner or customers.
    """

    business_id: BusinessId
    business_name: BusinessName | None = None
    country_code: CountryCode | None = None
    plan_key: PlanKey | None = None
    business_status: BusinessStatus | None = None
    code: ReferralCode
    referred_at: Microseconds
    first_paid_at: Microseconds | None = None


class PartnerReferralPage(ImmutableDTO):
    items: list[PartnerReferralView]
    next_cursor: PageCursor | None = None


class CommissionEntryView(ImmutableDTO):
    """
    A commission on one paid invoice: the business, the month it belongs
    to, what the invoice charged before tax, the rate and the share, and
    whether it was paid out (when, with what reference).
    """

    id: CommissionEntryId
    business_id: BusinessId
    business_name: BusinessName | None = None
    month: CommissionMonth
    base_minor: MoneyAmountMinor
    rate_basis_points: CommissionRateBasisPoints
    amount_minor: MoneyAmountMinor
    currency_code: CurrencyCode
    status: CommissionStatus
    accrued_at: Microseconds
    paid_at: Microseconds | None = None


class CommissionEntryPage(ImmutableDTO):
    items: list[CommissionEntryView]
    next_cursor: PageCursor | None = None
