"""
The reply guard's check of a deposit's amount: in a turn that asked a
deposit, a sentence of the assistant's own words that speaks of the
deposit may name no other amount than the one asked. The payment line
itself is the server's and is added after the check; any other amount of
the reply still passes the invented-numbers guard.
"""

import re
from collections.abc import Iterable, Sequence
from decimal import Decimal

from app.schemas.dto.billing import Money
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.money.money_math import convert_money_to_major_units
from app.utilities.reply_guard.deposit_terms import DEPOSIT_TERMS
from app.utilities.reply_guard.guard_lexicon import GuardLexicon, build_guard_lexicon
from app.utilities.reply_guard.invented_numbers import MAX_UNCHECKED_COUNT
from app.utilities.reply_guard.number_mention import NumberMention
from app.utilities.reply_guard.number_mentions import extract_number_mentions

SENTENCE_END: re.Pattern[str] = re.compile(r"(?<=[.!?。！？؟։।\n])\s*")


def find_deposit_amount_mismatches(
    reply: MessageText,
    asked: Sequence[DepositAmount],
    language_tags: Iterable[LanguageTag],
) -> list[UnverifiedReplyValue]:
    """
    Amounts the reply names for the deposit that no deposit of the turn
    asked, as written, in reply order and without repeats (none when the
    turn asked no deposit).
    """

    if not asked:
        return []

    lexicon: GuardLexicon = build_guard_lexicon(
        language_tags, {amount.currency_code for amount in asked}
    )
    allowed: frozenset[Decimal] = frozenset(major_amount(amount) for amount in asked)
    found: list[UnverifiedReplyValue] = []
    for sentence in SENTENCE_END.split(str(reply)):
        if not speaks_of_deposit(sentence):
            continue

        for mention in extract_number_mentions(sentence, lexicon):
            if not names_an_amount(mention) or mention.amounts & allowed:
                continue

            value = UnverifiedReplyValue(mention.text)
            if value not in found:
                found.append(value)

    return found


def speaks_of_deposit(sentence: str) -> bool:
    folded: str = sentence.casefold()
    return any(term in folded for term in DEPOSIT_TERMS)


def names_an_amount(mention: NumberMention) -> bool:
    """Money, or a bare number too large to be a count of guests."""

    if mention.is_money:
        return True

    return mention.is_plain_number and any(
        amount > MAX_UNCHECKED_COUNT for amount in mention.amounts
    )


def major_amount(amount: DepositAmount) -> Decimal:
    """5000 GEL minor units -> Decimal("50.00"), as the guard reads money."""

    return convert_money_to_major_units(
        Money(
            amount_minor=MoneyAmountMinor(int(amount.amount_minor)),
            currency_code=amount.currency_code,
        )
    ).normalize()
