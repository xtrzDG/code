"""Sums of partners' commissions as the database groups them."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.referrals import CommissionStatus
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.referrals.constrained_integers import CommissionInvoiceCount
from app.schemas.typings.referrals.prefixed_id import PartnerId


class CommissionTotal(ImmutableDTO):
    """
    The commissions of one partner in one currency and status: how many
    invoices earned them and how much in all (minor units).
    """

    partner_id: PartnerId
    currency_code: CurrencyCode
    status: CommissionStatus
    invoice_count: CommissionInvoiceCount
    amount_minor: MoneyAmountMinor
