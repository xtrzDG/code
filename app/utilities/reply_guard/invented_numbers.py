"""
Invented-numbers guard (concept section 5, "Защита от выдуманных цифр").

Every money amount, time, date, phone number and other number in an
assistant reply must appear in the evidence. Trusted evidence is what the
business and the server said: the version's facts, tool results and the
server-written context. Customer evidence is what the customer wrote (and
what the assistant already repeated from it): it may back times, dates,
phone numbers and counts the customer gave, but never a price or a
percentage (concept: a price comes only from get_price or the facts), and
a bare hour backs a full-hour time only when the customer wrote it as an
hour ("at 7" backs "19:00"; "table for 7" does not). Small counts (0 to 10)
written as plain numbers are not checked, since "2 guests" or "1 table"
invent nothing; small prices, percentages, times and dates are.
"""

from collections.abc import Iterable
from decimal import Decimal

from app.schemas.typings.conversations.strings import (
    MessageText,
    UnverifiedReplyValue,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.utilities.reply_guard.evidence_index import (
    EvidenceIndex,
    build_evidence_index,
)
from app.utilities.reply_guard.evidence_support import is_supported
from app.utilities.reply_guard.guard_lexicon import GuardLexicon, build_guard_lexicon
from app.utilities.reply_guard.number_mention import NumberMention
from app.utilities.reply_guard.number_mentions import extract_number_mentions

MAX_UNCHECKED_COUNT: Decimal = Decimal(10)


def find_unverified_values(
    reply: MessageText,
    evidence_texts: Iterable[str],
    language_tags: Iterable[LanguageTag],
    currency_codes: Iterable[CurrencyCode],
    customer_texts: Iterable[str] = (),
) -> list[UnverifiedReplyValue]:
    """
    Values of the reply that no evidence supports, as written, in reply
    order and without repeats. An empty list means the reply may be sent.

    `evidence_texts` are trusted (facts, tool results, server context);
    `customer_texts` are what the customer wrote, which never backs money.
    """

    lexicon: GuardLexicon = build_guard_lexicon(language_tags, currency_codes)
    trusted: EvidenceIndex = build_evidence_index(evidence_texts, lexicon)
    customer_text_list: list[str] = list(customer_texts)
    customer: EvidenceIndex = build_evidence_index(
        customer_text_list,
        lexicon,
        is_reading_hour_hints=True,
    )
    unverified_values: list[UnverifiedReplyValue] = []
    for mention in extract_number_mentions(str(reply), lexicon):
        if is_unchecked_count(mention) or is_supported(mention, trusted, customer):
            continue

        value = UnverifiedReplyValue(mention.text)
        if value not in unverified_values:
            unverified_values.append(value)

    return unverified_values


def is_unchecked_count(mention: NumberMention) -> bool:
    return mention.is_plain_number and all(
        amount == amount.to_integral_value() and 0 <= amount <= MAX_UNCHECKED_COUNT
        for amount in mention.amounts
    )
