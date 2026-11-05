"""
The amounts a policy asks, in any currency with its own minor units; the
report's no-show rates, honest below a small sample; the guard that keeps
the reply from naming another deposit than the one asked.
"""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.deposits import DepositRule, DepositStatus
from app.schemas.domain.deposits import BookingDepositPolicy
from app.schemas.dto.billing import Money
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.dto.deposits.deposit_counts import BookingOutcomeRow
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deposits.constrained_integers import (
    DepositAmountMinor,
    DepositDueMinor,
    DepositOutcomeCount,
    DepositPercent,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.deposits.deposit_amounts import due_deposit
from app.utilities.deposits.deposit_report_math import no_show_rate
from app.utilities.reply_guard.deposit_amount_check import (
    find_deposit_amount_mismatches,
)

GEL: CurrencyCode = CurrencyCode("GEL")


def policy(
    rule: DepositRule,
    amount_minor: int | None = None,
    percent: int | None = None,
    min_party_size: int | None = None,
    currency: str = "GEL",
) -> BookingDepositPolicy:
    return BookingDepositPolicy(
        rule=rule,
        amount_minor=None if amount_minor is None else DepositAmountMinor(amount_minor),
        percent=None if percent is None else DepositPercent(percent),
        currency_code=CurrencyCode(currency),
        min_party_size=None if min_party_size is None else PartySize(min_party_size),
    )


def money(amount_minor: int, currency: str) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor),
        currency_code=CurrencyCode(currency),
    )


def minor(amount: DepositAmount | None) -> int | None:
    return None if amount is None else int(amount.amount_minor)


def test_a_fixed_deposit_is_the_same_for_any_party() -> None:
    fixed = policy(DepositRule.FIXED, amount_minor=5000)

    assert minor(due_deposit(fixed, PartySize(2), None, GEL)) == 5000
    assert minor(due_deposit(fixed, PartySize(9), None, GEL)) == 5000


def test_a_per_guest_deposit_counts_the_guests_from_the_threshold() -> None:
    per_guest = policy(DepositRule.PER_GUEST, amount_minor=2000, min_party_size=6)

    assert due_deposit(per_guest, PartySize(5), None, GEL) is None
    assert minor(due_deposit(per_guest, PartySize(6), None, GEL)) == 12000


@pytest.mark.parametrize(
    ("value_minor", "currency", "percent", "expected"),
    [
        (12345, "GEL", 10, 1235),  # two digits: half up
        (999, "JPY", 30, 300),  # no minor units
        (10005, "KWD", 50, 5003),  # three digits
    ],
)
def test_a_percent_of_the_value_rounds_half_up_in_any_currency(
    value_minor: int, currency: str, percent: int, expected: int
) -> None:
    share = policy(DepositRule.PERCENT_OF_VALUE, percent=percent, currency=currency)

    due = due_deposit(
        share, PartySize(2), money(value_minor, currency), CurrencyCode(currency)
    )

    assert minor(due) == expected
    assert due is not None and str(due.currency_code) == currency


def test_a_percent_of_an_unknown_value_asks_nothing() -> None:
    share = policy(DepositRule.PERCENT_OF_VALUE, percent=20)

    assert due_deposit(share, PartySize(4), None, GEL) is None


def test_a_policy_in_another_currency_is_refused() -> None:
    in_dollars = policy(DepositRule.FIXED, amount_minor=5000, currency="USD")

    with pytest.raises(ValidationFailedError) as raised:
        due_deposit(in_dollars, PartySize(2), None, GEL)

    assert [str(reason.code) for reason in raised.value.reasons] == [
        "currency_mismatch"
    ]


def rows(
    with_paid: tuple[int, int], without: tuple[int, int]
) -> list[BookingOutcomeRow]:
    """(completed, no-shows) with a paid deposit and with none."""

    return [
        BookingOutcomeRow(
            status=BookingStatus.COMPLETED,
            deposit_status=DepositStatus.PAID,
            count=DepositOutcomeCount(with_paid[0]),
        ),
        BookingOutcomeRow(
            status=BookingStatus.NO_SHOW,
            deposit_status=DepositStatus.KEPT,
            count=DepositOutcomeCount(with_paid[1]),
        ),
        BookingOutcomeRow(
            status=BookingStatus.COMPLETED, count=DepositOutcomeCount(without[0])
        ),
        BookingOutcomeRow(
            status=BookingStatus.NO_SHOW, count=DepositOutcomeCount(without[1])
        ),
        # Not finished, or a deposit never paid: in neither group.
        BookingOutcomeRow(status=BookingStatus.CONFIRMED, count=DepositOutcomeCount(7)),
        BookingOutcomeRow(
            status=BookingStatus.NO_SHOW,
            deposit_status=DepositStatus.EXPIRED,
            count=DepositOutcomeCount(3),
        ),
    ]


def test_a_small_sample_says_not_enough_data() -> None:
    sample = rows(with_paid=(15, 4), without=(30, 10))

    with_deposit = no_show_rate(sample, with_deposit=True)
    without_deposit = no_show_rate(sample, with_deposit=False)

    assert int(with_deposit.finished_count) == 19
    assert with_deposit.has_enough_data is False
    assert with_deposit.no_show_percent is None
    assert int(without_deposit.finished_count) == 40
    assert without_deposit.has_enough_data is True
    assert int(without_deposit.no_show_percent or 0) == 25


def test_both_rates_once_each_has_twenty_finished_bookings() -> None:
    sample = rows(with_paid=(19, 1), without=(16, 4))

    assert int(no_show_rate(sample, with_deposit=True).no_show_percent or 0) == 5
    assert int(no_show_rate(sample, with_deposit=False).no_show_percent or 0) == 20


def asked(amount_minor: int) -> list[DepositAmount]:
    return [
        DepositAmount(amount_minor=DepositDueMinor(amount_minor), currency_code=GEL)
    ]


def test_the_reply_may_name_the_deposit_asked() -> None:
    reply = MessageText("Для брони нужен депозит 120 GEL. Ждём вас в 19:00!")

    assert (
        find_deposit_amount_mismatches(reply, asked(12000), [LanguageTag("ru")]) == []
    )


def test_another_deposit_amount_in_the_reply_is_caught() -> None:
    reply = MessageText("The deposit is 150 GEL, payable by the link below.")

    found = find_deposit_amount_mismatches(reply, asked(12000), [LanguageTag("en")])

    assert [str(value) for value in found] == ["150 GEL"]


def test_numbers_away_from_the_deposit_are_not_its_business() -> None:
    reply = MessageText("A table for 6 at 19:00 costs about 300 GEL in total.")

    assert (
        find_deposit_amount_mismatches(reply, asked(12000), [LanguageTag("en")]) == []
    )
