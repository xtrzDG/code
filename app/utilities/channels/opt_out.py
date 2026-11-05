"""
A customer's opt-out of messages they did not ask for (STOP / START) and
whether a contact may get such a message (customer-ai gap 12).

The opt-out is per channel (`ContactDocument.opted_out_channels`: where
the customer sent STOP; PHONE covers SMS to their number) and is honoured
everywhere: a customer who stopped messages in one channel gets no
reminder, feedback request or message after a missed call in any.
"""

import unicodedata

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import CustomerSignalKind
from app.schemas.domain.contacts import ContactDocument
from app.utilities.channels.opt_out_keywords import OPT_IN_KEYWORDS, OPT_OUT_KEYWORDS

# A keyword is the whole message; anything longer is a sentence the
# assistant answers.
MAX_COMMAND_LENGTH: int = 40
SURROUNDING_PUNCTUATION: str = " \t\r\n.!?,;:¡¿。！？、\"'«»“”„‘’()[]*_~"
SPACE_LIKE: str = "-‐‑–—_"


def normalize_command(text: str) -> str:
    """
    A message as the keyword tables hold it: NFKC, lower case (casefold),
    hyphens and dashes as spaces, single spaces, no surrounding punctuation
    or emoji presentation marks. A leading "/" (a bot command) is kept.
    """

    normalized: str = unicodedata.normalize("NFKC", text).casefold()
    normalized = normalized.replace("️", "")
    for mark in SPACE_LIKE:
        normalized = normalized.replace(mark, " ")

    return " ".join(normalized.split()).strip(SURROUNDING_PUNCTUATION)


def read_messaging_preference(text: str) -> CustomerSignalKind | None:
    """OPT_OUT for STOP and its translations, OPT_IN for START, else None."""

    if len(text) > MAX_COMMAND_LENGTH * 2:
        return None

    command: str = normalize_command(text)
    if command == "" or len(command) > MAX_COMMAND_LENGTH:
        return None

    if command in OPT_OUT_KEYWORDS:
        return CustomerSignalKind.OPT_OUT

    if command in OPT_IN_KEYWORDS:
        return CustomerSignalKind.OPT_IN

    return None


def is_opted_out(contact: ContactDocument | None) -> bool:
    """A customer who asked for no unrequested messages, in any channel."""

    return contact is not None and bool(contact.opted_out_channels)


def with_opt_out(contact: ContactDocument, channel: ChannelKind) -> list[ChannelKind]:
    """The contact's opted-out channels with this one added (kept in order)."""

    if channel in contact.opted_out_channels:
        return list(contact.opted_out_channels)

    return [*contact.opted_out_channels, channel]
