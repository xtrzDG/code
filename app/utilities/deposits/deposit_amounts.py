"""
Which deposit policy covers a booking or a banquet request, and what it
asks: a fixed sum, a sum per guest, or a percent of the booking's value,
rounded once to the precision of the currency (half up). Nothing is asked
of a party smaller than the policy's threshold, nor a percent of a booking
whose value is unknown.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.schemas.constants.deposits import (
    DepositRefusalCode,
    DepositRule,
    DepositTarget,
)
from app.schemas.domain.deposits import BookingDepositPolicy, TargetedDepositPolicy
from app.schemas.dto.billing import Money
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.deposits.deposit_refusals import deposit_refusal
from app.utilities.money.money_formatting import format_money
from app.utilities.money.money_math import ONE_HUNDRED_PERCENT, multiply_money

ENGLISH: LanguageTag = LanguageTag("en")


def booking_policy(
    policies: Sequence[TargetedDepositPolicy],
    resource_id: ResourceId,
    service_item_id: KnowledgeItemId | None,
) -> BookingDepositPolicy | None:
    """The service's policy when it has one, else the resource's."""

    if service_item_id is not None:
        for entry in policies:
            if (
                entry.target is DepositTarget.SERVICE
                and entry.service_item_id == service_item_id
            ):
                return entry.policy

    for entry in policies:
        if entry.target is DepositTarget.RESOURCE and entry.resource_id == resource_id:
            return entry.policy

    return None


def banquet_policy(
    policies: Sequence[TargetedDepositPolicy],
) -> BookingDepositPolicy | None:
    return next(
        (entry.policy for entry in policies if entry.target is DepositTarget.BANQUET),
        None,
    )


def due_deposit(
    policy: BookingDepositPolicy,
    party_size: PartySize | None,
    value: Money | None,
    business_currency: CurrencyCode,
) -> DepositAmount | None:
    """
    What the policy asks of this party (None: nothing).

    Raises:
        ValidationFailedError: the policy's currency is not the business's
            (the owner changed the currency after setting it).
    """

    if policy.currency_code != business_currency:
        raise deposit_refusal(
            DepositRefusalCode.CURRENCY_MISMATCH,
            f"The deposit policy is in {policy.currency_code}, the business "
            f"counts in {business_currency}: set the policy again.",
        )

    guests: int = 1 if party_size is None else int(party_size)
    if policy.min_party_size is not None and guests < int(policy.min_party_size):
        return None

    amount: Money | None = _policy_amount(policy, guests, value, business_currency)
    if amount is None or int(amount.amount_minor) < 1:
        return None

    return DepositAmount(
        amount_minor=DepositDueMinor(int(amount.amount_minor)),
        currency_code=amount.currency_code,
    )


def _policy_amount(
    policy: BookingDepositPolicy,
    guests: int,
    value: Money | None,
    business_currency: CurrencyCode,
) -> Money | None:
    if policy.rule is DepositRule.PERCENT_OF_VALUE:
        if (
            policy.percent is None
            or value is None
            or value.currency_code != business_currency
        ):
            return None

        return multiply_money(value, Decimal(int(policy.percent)) / ONE_HUNDRED_PERCENT)

    if policy.amount_minor is None:
        return None

    times: int = guests if policy.rule is DepositRule.PER_GUEST else 1
    return Money(
        amount_minor=MoneyAmountMinor(int(policy.amount_minor) * times),
        currency_code=business_currency,
    )


def deposit_amount_text(
    amount: DepositAmount, language: LanguageTag
) -> FormattedMoneyText:
    """The amount in the customer's language (English when CLDR has none)."""

    money = Money(
        amount_minor=MoneyAmountMinor(int(amount.amount_minor)),
        currency_code=amount.currency_code,
    )
    try:
        return format_money(money, language)
    except UnsupportedLanguageError:
        return format_money(money, ENGLISH)
