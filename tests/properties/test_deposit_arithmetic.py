"""
Deposit arithmetic (SDLC-07): whatever a policy says, a deposit is either
nothing or a positive amount in the business's currency; a fixed sum asks
exactly that, a sum per guest that times the party, a percent never more
than the booking's value and never less for a dearer booking; a party
below the policy's threshold, or a percent of an unknown value, asks
nothing.
"""

from hypothesis import given
from hypothesis import strategies as st

from app.schemas.constants.deposits import DepositRule
from app.schemas.domain.deposits import BookingDepositPolicy
from app.schemas.dto.billing import Money
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.deposits.constrained_integers import (
    DepositAmountMinor,
    DepositPercent,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.deposits.deposit_amounts import due_deposit

CURRENCIES: tuple[CurrencyCode, ...] = (
    CurrencyCode("EUR"),
    CurrencyCode("JPY"),  # no minor unit
    CurrencyCode("BHD"),  # three decimals
    CurrencyCode("GEL"),
)
currencies = st.sampled_from(CURRENCIES)
sums = st.integers(min_value=1, max_value=10**7)
parties = st.none() | st.integers(min_value=1, max_value=500).map(PartySize)
thresholds = st.none() | st.integers(min_value=1, max_value=50).map(PartySize)
percents = st.integers(min_value=1, max_value=100)
values = st.integers(min_value=0, max_value=10**9)


def policy(
    rule: DepositRule,
    currency: CurrencyCode,
    amount: int | None = None,
    percent: int | None = None,
    threshold: PartySize | None = None,
) -> BookingDepositPolicy:
    return BookingDepositPolicy(
        rule=rule,
        amount_minor=None if amount is None else DepositAmountMinor(amount),
        percent=None if percent is None else DepositPercent(percent),
        currency_code=currency,
        min_party_size=threshold,
    )


def money(amount: int, currency: CurrencyCode) -> Money:
    return Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency)


def minor(due: DepositAmount | None) -> int:
    return 0 if due is None else int(due.amount_minor)


@given(
    st.sampled_from(DepositRule),
    currencies,
    sums,
    percents,
    parties,
    thresholds,
    values,
)
def test_a_deposit_is_nothing_or_a_positive_sum_in_the_business_currency(
    rule: DepositRule,
    currency: CurrencyCode,
    amount: int,
    percent: int,
    party: PartySize | None,
    threshold: PartySize | None,
    value: int,
) -> None:
    due = due_deposit(
        policy(rule, currency, amount, percent, threshold),
        party,
        money(value, currency),
        currency,
    )

    assert due is None or (int(due.amount_minor) >= 1 and due.currency_code == currency)
    guests = 1 if party is None else int(party)
    if threshold is not None and guests < int(threshold):
        assert due is None


@given(currencies, sums, parties)
def test_a_fixed_sum_asks_exactly_it_and_a_sum_per_guest_times_the_party(
    currency: CurrencyCode, amount: int, party: PartySize | None
) -> None:
    guests = 1 if party is None else int(party)

    fixed = due_deposit(
        policy(DepositRule.FIXED, currency, amount), party, None, currency
    )
    per_guest = due_deposit(
        policy(DepositRule.PER_GUEST, currency, amount), party, None, currency
    )

    assert minor(fixed) == amount
    assert minor(per_guest) == amount * guests


@given(currencies, percents, values, values)
def test_a_percent_never_exceeds_the_value_and_grows_with_it(
    currency: CurrencyCode, percent: int, value: int, more: int
) -> None:
    rule = policy(DepositRule.PERCENT_OF_VALUE, currency, percent=percent)

    due = due_deposit(rule, None, money(value, currency), currency)
    dearer = due_deposit(rule, None, money(value + more, currency), currency)

    assert minor(due) <= value
    assert minor(due) <= minor(dearer)
    # Rounded once to the currency's precision: half a minor unit at most.
    assert abs(minor(due) * 100 - value * percent) <= 50
    assert due_deposit(rule, None, None, currency) is None
