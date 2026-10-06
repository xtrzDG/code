"""The platform team's side of the partner program: partners and payouts."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.referrals import PartnerStatus
from app.schemas.constants.users import LoginMethod
from app.schemas.dto.billing import Money
from app.schemas.dto.referrals.partner_portal import (
    CommissionTotalView,
    PartnerCodeView,
)
from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.referrals.constrained_integers import (
    CommissionInvoiceCount,
    CommissionRateBasisPoints,
    ReferredBusinessCount,
)
from app.schemas.typings.referrals.constrained_strings import (
    CommissionMonth,
    PartnerName,
    PayoutReference,
)
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import RawEmailAddressInput


class AdminPartnersQuery(ImmutableDTO):
    """A platform admin opens the partner list."""

    user_id: UserId


class PartnerAdminView(ImmutableDTO):
    """
    A partner as the platform team sees them: how they sign in, their rate
    and state, their codes, how many businesses they brought and paid, and
    their commissions per currency and status.
    """

    partner_id: PartnerId
    name: PartnerName
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    commission_rate_basis_points: CommissionRateBasisPoints
    status: PartnerStatus
    codes: list[PartnerCodeView] = Field(default_factory=list[PartnerCodeView])
    referred_businesses: ReferredBusinessCount
    paid_businesses: ReferredBusinessCount
    totals: list[CommissionTotalView] = Field(default_factory=list[CommissionTotalView])
    created_at: Microseconds


class PartnerList(ImmutableDTO):
    items: list[PartnerAdminView]


class CreatePartnerRequest(ImmutableDTO):
    """
    HTTP body of a new partner: their name, the phone number (any country;
    national formats read in `country_hint`) or e-mail they will sign in
    with, their commission rate in basis points (2000 = 20 %) and their
    first code.

    Example: {"name": "Tbilisi Digital", "email": "hello@tbd.example",
    "commission_rate_basis_points": 2000, "code": "tbilisi-digital"}.
    """

    name: PartnerName
    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    country_hint: CountryCode | None = None
    commission_rate_basis_points: CommissionRateBasisPoints
    code: ReferralCode


class CreatePartnerCommand(ImmutableDTO):
    user_id: UserId
    request: CreatePartnerRequest
    client_ip_address: ClientIpAddress | None = None


class UpdatePartnerRequest(ImmutableDTO):
    """
    HTTP body of a change of a partner; missing fields stay as they are.
    A new rate applies to invoices paid from now on.

    Example: {"status": "paused"}.
    """

    name: PartnerName | None = None
    commission_rate_basis_points: CommissionRateBasisPoints | None = None
    status: PartnerStatus | None = None


class UpdatePartnerCommand(ImmutableDTO):
    user_id: UserId
    partner_id: PartnerId
    request: UpdatePartnerRequest
    client_ip_address: ClientIpAddress | None = None


class AddPartnerCodeRequest(ImmutableDTO):
    """
    HTTP body of another code for a partner (a campaign of theirs).

    Example: {"code": "tbd-autumn"}.
    """

    code: ReferralCode


class AddPartnerCodeCommand(ImmutableDTO):
    user_id: UserId
    partner_id: PartnerId
    request: AddPartnerCodeRequest
    client_ip_address: ClientIpAddress | None = None


class PayoutReportQuery(ImmutableDTO):
    """The commissions of one month (UTC), per partner."""

    user_id: UserId
    month: CommissionMonth


class PayoutRowView(ImmutableDTO):
    """
    One partner's commissions of the month in one currency: what is still
    to be paid out and what was paid, with how many invoices each.
    """

    partner_id: PartnerId
    partner_name: PartnerName | None = None
    partner_status: PartnerStatus | None = None
    currency_code: CurrencyCode
    accrued_minor: MoneyAmountMinor
    accrued_invoices: CommissionInvoiceCount
    paid_minor: MoneyAmountMinor
    paid_invoices: CommissionInvoiceCount


class PayoutReportView(ImmutableDTO):
    month: CommissionMonth
    rows: list[PayoutRowView]


class MarkPayoutPaidRequest(ImmutableDTO):
    """
    HTTP body of a payout: the month whose commissions the partner was paid
    and how (the transfer's reference).

    Example: {"month": "2026-10", "reference": "TBC 2026-11-03 #88123"}.
    """

    month: CommissionMonth
    reference: PayoutReference


class MarkPayoutPaidCommand(ImmutableDTO):
    user_id: UserId
    partner_id: PartnerId
    request: MarkPayoutPaidRequest
    client_ip_address: ClientIpAddress | None = None


class PayoutReceipt(ImmutableDTO):
    """What a payout marked paid: how many commissions and how much."""

    partner_id: PartnerId
    month: CommissionMonth
    paid_invoices: CommissionInvoiceCount
    amounts: list[Money] = Field(default_factory=list[Money])
