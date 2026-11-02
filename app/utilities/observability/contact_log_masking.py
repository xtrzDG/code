"""
Phone numbers and e-mail addresses masked in log lines: a message and its
arguments may name a customer's or an owner's contact ("code sent to
+39 333 123 4567"), and logs are kept, searched and shipped to other
services. The handler's filter hands its formatter a masked copy of each
record, so the record itself (and every other handler: tests, Sentry) is
untouched, and the structured fields stay as they are.

Phone numbers are written the international way in this platform's
messages (E.164, `+` and 7 to 15 digits, possibly grouped): a bare run of
digits there is an id, an amount or a time, never masked.
"""

import copy
import logging
import re

from app.utilities.reply_guard.contact_details import EMAIL_PATTERN

EMAIL_PLACEHOLDER: str = "[email]"
PHONE_PLACEHOLDER: str = "[phone]"
# "+" then 7 to 15 digits with at most two separators between any two of them
# ("+393331234567", "+39 333 123 4567", "+1 (415) 555-0100").
INTERNATIONAL_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w+])\+\(?\d(?:[ ().\-]{0,2}\d){6,14}(?!\d)"
)


def mask_contact_details(text: str) -> str:
    """The text with e-mail addresses and international phone numbers masked."""

    without_emails: str = EMAIL_PATTERN.sub(EMAIL_PLACEHOLDER, text)
    return INTERNATIONAL_PHONE_PATTERN.sub(PHONE_PLACEHOLDER, without_emails)


class ContactDetailsLogFilter(logging.Filter):
    """
    Masks the contacts in a record's message with its arguments filled in.
    Returns a masked copy (Python 3.12+: the handler emits the copy), or the
    record itself when there was nothing to mask.
    """

    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        try:
            message: str = record.getMessage()
        except Exception:  # the formatter reports a broken format itself
            return True

        masked: str = mask_contact_details(message)
        if masked == message:
            return True

        masked_record: logging.LogRecord = copy.copy(record)
        masked_record.msg = masked
        masked_record.args = None
        return masked_record
