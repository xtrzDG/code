"""
Whether a booking or a banquet request needs a deposit, and how much:
deposits must be on, a policy must cover it (a service's over its
resource's; the banquets' for a banquet request), the party must reach
the policy's threshold, and a percent needs the booking's value.
"""

from dataclasses import dataclass

from app.schemas.constants.bookings import LeadType
from app.schemas.constants.deposits import DepositExemption, DepositRule
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.deposits import BookingDepositPolicy, DepositSettingsDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.deposits.deposit_amounts import (
    banquet_policy,
    booking_policy,
    due_deposit,
)


@dataclass(frozen=True)
class QuotedDeposit:
    """The amount and the policy that asks it, or why nothing is asked."""

    amount: DepositAmount | None = None
    policy: BookingDepositPolicy | None = None
    exemption: DepositExemption | None = None


def quote_booking(
    settings: DepositSettingsDocument | None,
    booking: BookingDocument,
    business_currency: CurrencyCode,
) -> QuotedDeposit:
    if settings is None or not settings.is_enabled:
        return QuotedDeposit(exemption=DepositExemption.DEPOSITS_OFF)

    policy: BookingDepositPolicy | None = booking_policy(
        settings.policies, booking.resource_id, booking.service_item_id
    )
    value: Money | None = (
        None
        if booking.value_minor is None or booking.currency_code is None
        else Money(
            amount_minor=MoneyAmountMinor(int(booking.value_minor)),
            currency_code=booking.currency_code,
        )
    )
    return quote(policy, booking.party_size, value, business_currency)


def quote_banquet(
    settings: DepositSettingsDocument | None,
    lead: LeadDocument,
    business_currency: CurrencyCode,
) -> QuotedDeposit:
    if settings is None or not settings.is_enabled:
        return QuotedDeposit(exemption=DepositExemption.DEPOSITS_OFF)

    if lead.lead_type is not LeadType.BANQUET:
        return QuotedDeposit(exemption=DepositExemption.NOT_A_BANQUET)

    return quote(
        banquet_policy(settings.policies), lead.party_size, None, business_currency
    )


def quote(
    policy: BookingDepositPolicy | None,
    party_size: PartySize | None,
    value: Money | None,
    business_currency: CurrencyCode,
) -> QuotedDeposit:
    if policy is None:
        return QuotedDeposit(exemption=DepositExemption.NO_POLICY)

    amount: DepositAmount | None = due_deposit(
        policy, party_size, value, business_currency
    )
    if amount is not None:
        return QuotedDeposit(amount=amount, policy=policy)

    if policy.rule is DepositRule.PERCENT_OF_VALUE and value is None:
        return QuotedDeposit(exemption=DepositExemption.VALUE_UNKNOWN)

    return QuotedDeposit(exemption=DepositExemption.SMALL_PARTY)
