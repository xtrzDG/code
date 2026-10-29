"""
What a call's transcript keeps when the caller declined the recording: the
words, without the numbers and addresses that identify or reach a person.

E-mail addresses, IBAN-style account numbers, payment card numbers (13 to
19 digits) and phone or other long numbers (7 to 15 digits, the shape
`PHONE_PATTERN` finds) become placeholders. Dates, times, prices, party
sizes and room numbers stay, so staff still see what was agreed: a long
number written as a date (25.10.2026, 25/10/2026, 2026-10-25) or as an
amount next to its currency (1 500 000 som, $ 2 400 000, 1500000 UZS) is
not a phone number. Numbers the speech recognizer wrote as words are not
found.
"""

import re

from app.utilities.observability.trace_redaction import (
    PHONE_PATTERN,
    PHONE_PLACEHOLDER,
)
from app.utilities.reply_guard.contact_details import EMAIL_PATTERN

EMAIL_PLACEHOLDER: str = "[email]"
ACCOUNT_PLACEHOLDER: str = "[account number]"
CARD_PLACEHOLDER: str = "[card number]"
# Two letters, two check digits and 10 to 30 letters or digits, spaced in
# groups of four or not (IBAN, e.g. GE29 NB00 0000 0101 9049 17).
ACCOUNT_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w])[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{2,4}){3,8}(?![\w])"
)
# 13 to 19 digits with single spaces or hyphens between them.
CARD_PATTERN: re.Pattern[str] = re.compile(r"(?<![\w+])\d(?:[ \-]?\d){12,18}(?![\w])")
# A calendar date, day first or year first, with one kind of separator.
DATE_PATTERN: re.Pattern[str] = re.compile(
    r"(?:0?[1-9]|[12]\d|3[01])([./\-])(?:0?[1-9]|1[0-2])\1(?:19|20)\d{2}"
    r"|(?:19|20)\d{2}([./\-])(?:0?[1-9]|1[0-2])\2(?:0?[1-9]|[12]\d|3[01])"
)
# Currency signs and the currency words callers of the platform's countries
# say (ISO codes are any three capitals).
CURRENCY_SIGNS: str = "$€£¥₹₽₾₸₺₴₼֏₪"
CURRENCY_WORD_PATTERN: re.Pattern[str] = re.compile(
    r"[A-Z]{3}(?![A-Za-z])"
    r"|(?i:som|soum|sum|сум|сом|сомов|lari|лари|рубл\w*|руб|dollars?|доллар\w*"
    r"|euros?|евро|tenge|тенге|drams?|драм\w*|manat|манат\w*|lira|лир\w*"
    r"|hryvnias?|гривен\w*|гривн\w*|shekels?|шекел\w*|zł|zloty|złotych)(?!\w)"
)
AMOUNT_BEFORE: re.Pattern[str] = re.compile(rf"[{CURRENCY_SIGNS}]\s?$")
AMOUNT_AFTER: re.Pattern[str] = re.compile(
    rf"^\s?(?:[{CURRENCY_SIGNS}]|{CURRENCY_WORD_PATTERN.pattern})"
)


def redact_call_text(text: str) -> str:
    """One spoken line without e-mail, account, card and phone numbers."""

    without_emails: str = EMAIL_PATTERN.sub(EMAIL_PLACEHOLDER, text)
    without_accounts: str = ACCOUNT_PATTERN.sub(ACCOUNT_PLACEHOLDER, without_emails)
    without_cards: str = CARD_PATTERN.sub(CARD_PLACEHOLDER, without_accounts)
    return PHONE_PATTERN.sub(_number_placeholder, without_cards)


def _number_placeholder(match: re.Match[str]) -> str:
    found: str = match.group(0)
    if DATE_PATTERN.fullmatch(found) or _is_amount(match):
        return found

    return PHONE_PLACEHOLDER


def _is_amount(match: re.Match[str]) -> bool:
    """A number said with its currency: a price, not a number to call."""

    if match.group(0).startswith("+"):
        return False

    before: str = match.string[max(0, match.start() - 2) : match.start()]
    after: str = match.string[match.end() : match.end() + 16]
    return bool(AMOUNT_BEFORE.search(before) or AMOUNT_AFTER.search(after))
