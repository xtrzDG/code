"""
Phone numbers and e-mail addresses taken out of the texts sent to the
quality journal (Langfuse) unless LANGFUSE_RAW_TEXT=true: a trace keeps
what the customer asked and the assistant answered, not how to reach them.
"""

import re

from app.utilities.reply_guard.contact_details import EMAIL_PATTERN

EMAIL_PLACEHOLDER: str = "[email]"
PHONE_PLACEHOLDER: str = "[phone]"
# 7 to 15 digits (E.164 allows 15) with at most two separators between
# them, an optional leading "+": local and international numbers in their
# usual groupings. Shorter runs (prices, times, room numbers) stay.
PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w+(])\+?\(?\d(?:[ ().\-]{0,2}\d){6,14}(?![\w])"
)
# Dates written the ISO way have eight digits too; they are not numbers to
# call.
ISO_DATE_PATTERN: re.Pattern[str] = re.compile(r"\d{4}-\d{2}-\d{2}")


def redact_contact_details(text: str) -> str:
    """The text with e-mail addresses and phone numbers replaced by placeholders."""

    without_emails: str = EMAIL_PATTERN.sub(EMAIL_PLACEHOLDER, text)
    return PHONE_PATTERN.sub(_phone_placeholder, without_emails)


def _phone_placeholder(match: re.Match[str]) -> str:
    found: str = match.group(0)
    if ISO_DATE_PATTERN.fullmatch(found):
        return found

    return PHONE_PLACEHOLDER
