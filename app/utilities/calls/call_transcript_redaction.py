"""
What a call's transcript keeps when the caller declined the recording: the
words, without the numbers and addresses that identify or reach a person.

E-mail addresses, IBAN-style account numbers, payment card numbers (13 to
19 digits) and phone or other long numbers (7 to 15 digits, the way
`redact_contact_details` finds them) become placeholders; dates, times,
prices, party sizes and room numbers stay, so staff still see what was
agreed. Numbers the speech recognizer wrote as words are not found.
"""

import re

from app.utilities.observability.trace_redaction import redact_contact_details
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


def redact_call_text(text: str) -> str:
    """One spoken line without e-mail, account, card and phone numbers."""

    without_emails: str = EMAIL_PATTERN.sub(EMAIL_PLACEHOLDER, text)
    without_accounts: str = ACCOUNT_PATTERN.sub(ACCOUNT_PLACEHOLDER, without_emails)
    without_cards: str = CARD_PATTERN.sub(CARD_PLACEHOLDER, without_accounts)
    return redact_contact_details(without_cards)
