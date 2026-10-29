"""Short calls into the reply guard: number mentions and unverified values."""

from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.reply_guard.guard_lexicon import build_guard_lexicon
from app.utilities.reply_guard.invented_numbers import find_unverified_values
from app.utilities.reply_guard.number_mention import NumberMention
from app.utilities.reply_guard.number_mentions import extract_number_mentions


def languages(*tags: str) -> list[LanguageTag]:
    return [LanguageTag(tag) for tag in tags]


def mentions(text: str, currency: str, *tags: str) -> list[NumberMention]:
    lexicon = build_guard_lexicon(languages(*tags), [CurrencyCode(currency)])
    return extract_number_mentions(text, lexicon)


def unverified(
    reply: str,
    evidence: list[str],
    currency: str,
    *tags: str,
    customer: list[str] | None = None,
) -> list[str]:
    return [
        str(value)
        for value in find_unverified_values(
            MessageText(reply),
            evidence,
            languages(*tags),
            [CurrencyCode(currency)],
            customer_texts=customer or [],
        )
    ]
