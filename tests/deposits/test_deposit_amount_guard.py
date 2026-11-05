"""
The deposit guard flags only another sum of money in a sentence about the
deposit. What the tool told the model to say (the place is held until
held_until, which names a day when the hold ends tomorrow), a booking's
number, a year or a banquet's guest count are no deposit amounts; the
invented-numbers guard checks those against the turn's evidence.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from typed_time_provider import Microseconds

from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.deposits.deposit_times import hold_end_text
from app.utilities.reply_guard.deposit_amount_check import (
    find_deposit_amount_mismatches,
)

TBILISI: ZoneInfo = ZoneInfo("Asia/Tbilisi")
# Asked at 22:30; the hold ends at 11:00 the next day.
ASKED_AT: datetime = datetime(2026, 10, 13, 22, 30, tzinfo=TBILISI)
HOLD_ENDS: datetime = datetime(2026, 10, 14, 11, 0, tzinfo=TBILISI)
DEPOSIT: list[DepositAmount] = [
    DepositAmount(
        amount_minor=DepositDueMinor(12000), currency_code=CurrencyCode("GEL")
    )
]


def mismatches(text: str, language: str) -> list[str]:
    return [
        str(value)
        for value in find_deposit_amount_mismatches(
            MessageText(text), DEPOSIT, [LanguageTag(language)]
        )
    ]


def held_until(language: str) -> str:
    """held_until as the tool gives it to the model, in the guest's language."""

    return str(
        hold_end_text(
            Microseconds(int(HOLD_ENDS.timestamp() * 1_000_000)),
            Microseconds(int(ASKED_AT.timestamp() * 1_000_000)),
            TBILISI,
            LanguageTag(language),
        )
    )


@pytest.mark.parametrize(
    ("language", "template"),
    [
        (
            "en",
            "We are holding your table until {until}; it is confirmed once "
            "the deposit is paid.",
        ),
        ("ru", "Держим столик до {until}, бронь подтвердится после оплаты депозита."),
        (
            "ka",
            "მაგიდას გინახავთ {until}-მდე, ჯავშანი დადასტურდება დეპოზიტის "
            "გადახდისთანავე.",
        ),
    ],
)
def test_a_hold_that_ends_tomorrow_is_no_deposit_amount(
    language: str, template: str
) -> None:
    until = held_until(language)
    assert "14" in until

    assert mismatches(template.format(until=until), language) == []


@pytest.mark.parametrize(
    "text",
    [
        "The deposit for booking #4521 is GEL 120.00.",
        "Deposits for 2026 bookings are paid by the link below.",
        "A banquet for 40 guests needs a deposit of 120 GEL.",
    ],
)
def test_numbers_that_are_no_money_pass(text: str) -> None:
    assert mismatches(text, "en") == []


@pytest.mark.parametrize(
    ("text", "language", "flagged"),
    [
        ("The deposit is 150 GEL, payable by the link below.", "en", "150 GEL"),
        ("Депозит 50 ₾, держим столик до 21:00.", "ru", "50 ₾"),
        ("დეპოზიტი 80 ₾ იქნება.", "ka", "80 ₾"),
    ],
)
def test_another_sum_for_the_deposit_is_still_caught(
    text: str, language: str, flagged: str
) -> None:
    found = mismatches(text, language)

    assert len(found) == 1
    assert found[0].startswith(flagged)
